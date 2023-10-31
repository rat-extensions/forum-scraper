import asyncio
import traceback

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from database import *

scraperConfig = fileToDictionary("config_scraper.ini")


def init_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--no-sandbox")
    if scraperConfig["headless"] == 1:
        chrome_options.add_argument("--headless=new")
    # chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    idontcareaboutcookiesPath = scraperConfig["iDontCareAboutCookiesPath"]
    chrome_options.add_extension(idontcareaboutcookiesPath)
    # driver = webdriver.Chrome(executable_path="/home/y/Downloads/chromedriver/chromedriver", options=chrome_options)
    # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver = webdriver.Chrome(service=Service(), options=chrome_options)
    driver.implicitly_wait(scraperConfig["waitTime"])
    driver.set_page_load_timeout(15)
    return driver


def isInactiveCommentSection(date):
    """
    Checks whether a comment section can be considered inactive.
    Inactivty = If the date (newest comment) was posted more than X days ago the comment section is considered inactive.

    The time after a comment section is considered inactive is determined via the scraper config.
    :param date:
    :return:
    """
    DAYINSECONDS = 86400
    stopScrapingAfterXDays = scraperConfig["stopScrapingAfterXDaysOfInactivity"]
    cutoff = stopScrapingAfterXDays * DAYINSECONDS
    epochtimeNow = time.time()
    isInactive = stopScrapingAfterXDays > 0 and (date is not None and (
            epochtimeNow - cutoff > date))  # TODO Vergleich so richtig? wenn der neuste Kommentar vor mehr als X Tagen verfassst wurde, dann gilt diese Kommentarsektion als inaktiv
    return isInactive


def determineValidUrls(driver, arcticleUrls, newspageUrls):
    """
    Determines which Urls are valid i.e. which urls lead to articles with a scrapable comment section.
    :param driver:
    :param arcticleUrls:
    :return:
    """
    waitTime = scraperConfig["waitTime"]
    validArticleUrlsFromFileDf = pd.DataFrame(columns=["url", "newspageurl", "isactivelyscraped"])
    for articleUrl in arcticleUrls:
        newspageUrl = determineNewspageUrl(newspageUrls, articleUrl)
        if newspageUrl is not None:
            scraper = determineScraper(newspageUrl)
            if scraper is not None:
                try:
                    driver.get(articleUrl)
                except TimeoutException:
                    log("Error Timeout when loading url: " + articleUrl)
                    continue
                    pass
                time.sleep(waitTime)
                try:
                    commentSectionExists = asyncio.run(asyncio.wait_for(scraper.commentSectionExists(driver), timeout=(5 + waitTime)))  # When Checking if CS exists the programm sometimes doesn't continue
                except TimeoutError:
                    log("Error Timeout when checking if comment section exists: " + articleUrl)
                    continue
                    pass
                if commentSectionExists:
                    newArticle = {"url": articleUrl, "newspageurl": newspageUrl}
                    validArticleUrlsFromFileDf = validArticleUrlsFromFileDf._append(newArticle, ignore_index=True)
                    log("Url was added to the database: " + articleUrl)
                else:
                    log("Error No scrapable comment section found: " + articleUrl)
            else:
                log("Error invalid url: " + articleUrl)
        else:
            log("Error invalid url: " + articleUrl)
    return validArticleUrlsFromFileDf


def main():
    try:
        articleUrl = None
        driver = init_driver()
        newspagesDf = fetchAllNewspages()
        newspageUrls = newspagesDf["url"].tolist()

        # Read Article URLs from CSV File and if the url is valid (i.e. article with a scrapable commentsection) add them to DB and enable Scraping
        articleUrlsFromFile = csvFileToList("article_urls.csv")
        # Tuple format:(ArticleUrl, isActivelyScraped) isAcitvelyScraped meaning 1=enable scraping, 0=disable scraping
        articleUrlsFromFile = [(aUrl[0], aUrl[1])for aUrl in articleUrlsFromFile if len(aUrl) == 2]
        articleUrlsToScrape = [aUrlTuple[0] for aUrlTuple in articleUrlsFromFile if aUrlTuple[1] == '1']
        articleUrlsNotToScrape = [aUrlTuple[0] for aUrlTuple in articleUrlsFromFile if aUrlTuple[1] == '0']

        fileNotEmpty = len(articleUrlsToScrape) > 0
        if fileNotEmpty:
            validArticleUrlsFromFileDf = determineValidUrls(driver, articleUrlsToScrape, newspageUrls)
            validArticleUrlsFromFileDf["isactivelyscraped"] = 1  # enable scraping
            validArticleUrlsExist = len(validArticleUrlsFromFileDf.index) > 0
            if validArticleUrlsExist:
                validArticleUrlsFromFileDf = removeDuplicates(validArticleUrlsFromFileDf)
                insertNewsarticle(validArticleUrlsFromFileDf)

        # Disable scraping for given urls
        fileNotEmpty = len(articleUrlsNotToScrape) > 0
        if fileNotEmpty:
            updateArticleIsActivelyScraped(articleUrlsNotToScrape, setting=0)

    except Exception as e:
        log("Error Occured! Exception: " + str(e) + "\n" +
            "Stack trace: " + str(traceback.print_exc()))
        traceback.print_exc()

    finally:
        driver.quit()

    # For each url, checks if cs exists, show comments, scrape and insert data to db
    try:
        driver = init_driver()
        scrapeUpdateReactions = scraperConfig["scrapeAndUpdateReactions"] == 1
        scrapeResponses = scraperConfig["scrapeResponses"] == 1
        updateDeletedInfo = scraperConfig["updateDeletedInfo"] == 1
        waitTime = scraperConfig["waitTime"]

        allArticlesDf = fetchActivelyScrapedNewsarticle()

        for article in allArticlesDf.itertuples():
            try:
                articleUrl = getattr(article, "url")
                log("Article: " + articleUrl)
                dateNewestComment = fetchDateNewestComment(articleUrl)
                isInactiveCS = isInactiveCommentSection(dateNewestComment)
                stopScrapingAfterXDays = scraperConfig["stopScrapingAfterXDaysOfInactivity"]
                stopScrapingDisabled = stopScrapingAfterXDays == 0
                if (not isInactiveCS) or stopScrapingDisabled:
                    newspageUrl = determineNewspageUrl(newspageUrls, articleUrl)
                    scraper = determineScraper(newspageUrl)
                    if dateNewestComment is None:
                        dateNewestComment = 0
                    try:
                        driver.get(articleUrl)
                    except TimeoutException:
                        log("Error Timeout when loading url: " + articleUrl)
                        continue
                    time.sleep(waitTime)
                    try:
                        commentSectionExists = asyncio.run(asyncio.wait_for(scraper.commentSectionExists(driver),
                                                                            timeout=(
                                                                                        5 + waitTime)))  # When Checking if CS exists the programm sometimes doesn't continue
                    except TimeoutError:
                        log("Error Timeout when checking if comment section exists: " + articleUrl)
                        continue

                    if commentSectionExists:  # ensure that comment section didn't got hidden or something else
                        scraper.openCommentSection(driver)
                        log("Show comments.")
                        if scrapeResponses:
                            scraper.showAllComments(driver)
                        elif not scrapeResponses and (scrapeUpdateReactions or updateDeletedInfo): #if we want to update information we need to see every comment (since time 0)
                            scraper.showNewLevel0Comments(driver, 0)
                        elif not scrapeResponses:
                            scraper.showNewLevel0Comments(driver, dateNewestComment)

                        log("Start scraping.")
                        pageSource = driver.page_source
                        soup = BeautifulSoup(pageSource, "lxml")
                        commentsDf = scraper.scrapeComments(driver, dateNewestComment, soup)

                        # add article URL and newspage - newspage later needed for userid
                        commentsDf["articleurl"] = articleUrl
                        commentsDf["newspageurl"] = newspageUrl
                        log("Scraped :" + str(len(commentsDf.index)) + " comments from: " + articleUrl + "\n")

                        # Determine news users and insert into the dbd
                        dfToInsertForUserCreation = commentsDf[
                            commentsDf["username"].notnull()]  # remove rows where username is None
                        newUsersExist = len(dfToInsertForUserCreation.index) > 0
                        if newUsersExist:
                            insertUsers(dfToInsertForUserCreation)

                        reactionsDf = commentsDf[["cid", "articleurl", "upvotes", "downvotes", "loves",
                                                "likes", "stars", "hearts", "smiles", "frowns", "eyebrows",
                                                "astonisheds"]].copy()

                        # Remove duplicates and insert comments and reactions into the db -  Duplicates only occur very rarely
                        newCommentsExist = len(commentsDf.index) > 0
                        if newCommentsExist:
                            commentsDf = removeDuplicates(commentsDf)
                            insertComments(commentsDf)

                        reactionsExist = len(reactionsDf.index) > 0
                        if scrapeUpdateReactions and reactionsExist:
                            reactionsDf = removeDuplicates(reactionsDf)
                            insertreactions(reactionsDf)
                else:
                    log("Since the last scraped comment was posted more than " + stopScrapingAfterXDays + " days ago, no scraping was performed for: " + articleUrl)

            except Exception as e:
                log("Article URL: " + articleUrl + "\n" +
                    "A scraping related Error occured! Exception: " + str(e) + "\n")
                traceback.print_exc()
    except Exception as e:
        log("Error occured! Exception: " + str(e))
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
