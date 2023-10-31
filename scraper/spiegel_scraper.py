import calendar
import os.path
import time

import pandas as pd
from selenium.common import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scraper.scraper_interface import InformalScraperInterface
from utils import *


class SpiegelScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))
    waitTime = scraperConfig["waitTime"]

    def acceptCookies(self, driver):
        """Accepts Spiegel Online Cookie Popup - Not needed anymore, cookie banners are now taken care of by Plugin."""
        # Accept and continue - Continue reading with ads and tracking
        iframePopUpXpath = "//iframe[starts-with(@id, 'sp_message_iframe_') and @title='Privacy Center']"
        WebDriverWait(driver, self.waitTime).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframePopUpXpath))
        )
        acceptAndContinueButtonXPath = "//button[@class='message-component message-button no-children focusable primary-button font-sansUI font-bold sp_choice_type_11 first-focusable-el' and @title='Accept and continue']"
        acceptAndContinueElement = WebDriverWait(driver, self.waitTime).until(
            EC.element_to_be_clickable((By.XPATH, acceptAndContinueButtonXPath))
        )
        acceptAndContinueElement.click()
        driver.switch_to.default_content()

    def commentSectionExists(self, driver):
        commentSectionButtonXpath = "//button[@class='leading-normal font-bold bg-primary-base dark:bg-dm-primary-base inline-block border border-primary-base dark:border-dm-primary-base hover:border-primary-dark focus:border-primary-darker disabled:border-shade-lighter hover:bg-primary-dark focus:bg-primary-darker disabled:bg-shade-lighter dark:disabled:bg-shade-darker disabled:text-shade-dark dark:disabled:text-shade-light disabled:cursor-not-allowed text-white dark:text-shade-lightest font-sansUI pl-24 pr-20 py-12 my-8 text-base rounded outline-focus']"
        commentSectionButton = driver.find_elements(By.XPATH,
                                                    commentSectionButtonXpath)  # Button to open the comment section only exist if the commentsection is enabled
        commentSectionExists = len(commentSectionButton) > 0
        if commentSectionExists:
            return True
        else:
            return False

    def openCommentSection(self, driver):
        # Open comment section for article and switch to comment iframe
        commentSectionButtonXpath = "//button[@class='leading-normal font-bold bg-primary-base dark:bg-dm-primary-base inline-block border border-primary-base dark:border-dm-primary-base hover:border-primary-dark focus:border-primary-darker disabled:border-shade-lighter hover:bg-primary-dark focus:bg-primary-darker disabled:bg-shade-lighter dark:disabled:bg-shade-darker disabled:text-shade-dark dark:disabled:text-shade-light disabled:cursor-not-allowed text-white dark:text-shade-lightest font-sansUI pl-24 pr-20 py-12 my-8 text-base rounded outline-focus']"
        commentSectionButton = WebDriverWait(driver, self.waitTime).until(
            EC.element_to_be_clickable((By.XPATH, commentSectionButtonXpath)))
        driver.execute_script("arguments[0].click()", commentSectionButton)
        iframeCommentSectionXpath = "//*[starts-with(@id,'_0.') and contains(@id,'_iframe')]"
        iframeComments = WebDriverWait(driver, self.waitTime).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframeCommentSectionXpath))
        )
        # show All Comments comments and not recommended comment
        # e.g. https://www.spiegel.de/ausland/kolumbien-kinder-nach-40-tagen-im-dschungel-gerettet-wie-das-wunder-vom-amazonas-gelang-a-07960d33-b0af-43cb-b011-0e6725964894#kommentare
        showAllCommentsButtonXpath = "//button[contains(@class,'talk-tab-button Tab__buttonSub___2GrIi reset__buttonReset___1atdk')]"
        showCommentsButton = WebDriverWait(driver, self.waitTime).until(
            EC.element_to_be_clickable((By.XPATH, showAllCommentsButtonXpath))
        )
        if showCommentsButton:
            try:
                driver.execute_script("arguments[0].click()", showCommentsButton)
            except ElementClickInterceptedException:
                pass

    def showAllComments(self, driver):
        showMoreButtonXpath = "//button[contains(@class,'talk-load-more-button')]"
        showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreButtonXpath)
        while len(showMoreCommentsButtons) > 0:
            button = showMoreCommentsButtons[0]
            driver.execute_script("arguments[0].click()", button)
            time.sleep(1)
            showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreButtonXpath)

    def showNewLevel0Comments(self, driver, date):
        showMoreCommentsButtonXpath = "//button[contains(@class,'talk-load-more-button') and contains(text(), 'Weitere Kommentare anzeigen')]"
        commentLevelOXpath = "//div[@class='talk-stream-comment talk-stream-comment-level-0 Comment__comment___3_T6p Comment__commentLevel0___1B4Fw']"
        commentsLevel0 = driver.find_elements(By.XPATH, commentLevelOXpath)

        showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreCommentsButtonXpath)
        onlyNewLevel0CommentsVisible = self.getCommentDate(commentsLevel0[-1]) > date
        while (onlyNewLevel0CommentsVisible) and (len(showMoreCommentsButtons) > 0):
            button = showMoreCommentsButtons[0]
            driver.execute_script("arguments[0].click()", button)
            time.sleep(1)
            commentsLevel0 = driver.find_elements(By.XPATH,
                                                  commentLevelOXpath)
            onlyNewLevel0CommentsVisible = self.getCommentDate(commentsLevel0[-1]) > date
            showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreCommentsButtonXpath)

    def getCommentDate(self, comment):
        timestampXpath = ".//span[@class='CommentTimestamp__timestamp___2Ejbf talk-comment-timestamp TimeAgo__timeago___3aHze talk-comment-timeago']"
        timestamp = comment.find_element(By.XPATH, timestampXpath).get_attribute("title")
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%m/%d/%Y, %I:%M:%S %p"))
        return timestampEpoch

    def createCommentText(self, commentTextSpans):
        commentText = ""
        for commentTextSpan in commentTextSpans:
            commentText += commentTextSpan.text + "\n"
        commentText = commentText[:-1]  # remove last linebreak
        return commentText

    def createCommentDf(self, commentWrapper, date):
        commentLevel = int(
            commentWrapper.get_attribute("class").split(
                "talk-stream-comment-wrapper talk-stream-comment-wrapper-level-", 1)[1][0])
        commentId = commentWrapper.get_attribute("id")
        parentId = None
        if commentLevel != 0:  # Level0 comments have no parent
            parentCommentXpath = "./../.."
            parentComment = commentWrapper.find_element(By.XPATH, parentCommentXpath)
            parentId = parentComment.get_attribute("id")
        try:
            commentXpath = f".//div/div[contains(@class, 'talk-stream-comment talk-stream-comment-level-{commentLevel}')]"
            comment = commentWrapper.find_element(By.XPATH, commentXpath)
        except NoSuchElementException:  # Kommentar gelöscht
            deletedComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": None, "comment": None,
                                            "timestamp": None, "deleted": 1,
                                            "upvotes": None, "downvotes": None, "loves": None, "likes": None,
                                            "stars": None,
                                            "hearts": None,
                                            "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
            return deletedComment

        isNewComment = self.getCommentDate(comment) > date
        scrapeUpdateReactions = self.scraperConfig["scrapeAndUpdateReactions"] == 1
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if isNewComment or scrapeUpdateReactions or scrapeCommentResponses:
            deleted = 0
            userName = comment.find_element(By.XPATH, ".//span[@class='AuthorName__name___3O4jF']").text
            timestampEpoch = self.getCommentDate(comment)
            upvotes = None
            downvotes = None
            if scrapeUpdateReactions:
                upvotes = comment.find_element(By.XPATH, ".//span[@class='talk-plugin-upvote-count']").text
                if upvotes == "":
                    upvotes = 0
                downvotes = comment.find_element(By.XPATH,
                                                 ".//span[@class='talk-plugin-downvote-count']").text
                if downvotes == "":
                    downvotes = 0

            commentContent = comment.find_element(By.XPATH,
                                                  ".//div[@class='talk-stream-comment-content talk-slot-comment-content']")
            commentTextSpans = commentContent.find_elements(By.XPATH, ".//span[@class='Linkify']")
            commentText = self.createCommentText(commentTextSpans)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": upvotes, "downvotes": downvotes, "loves": None,
                                        "likes": None,
                                        "stars": None, "hearts": None,
                                        "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        return newComment

    def scrapeComments(self, driver, date):
        commentsDf = pd.DataFrame(
            columns=["cid", "parentid", "username", "comment", "timestamp", "deleted", "upvotes", "downvotes", "loves",
                     "likes",
                     "stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"])
        commentsWrapperXpath = "//div[contains(@class, 'talk-stream-comment-wrapper talk-stream-comment-wrapper-level')]"
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if not scrapeCommentResponses:
            commentsWrapperXpath = "//div[contains(@class, 'talk-stream-comment-wrapper talk-stream-comment-wrapper-level-0')]"
        commentWrapper = driver.find_elements(By.XPATH, commentsWrapperXpath)
        for cw in commentWrapper:
            newComment = self.createCommentDf(cw, date)
            commentsDf = commentsDf._append(newComment, ignore_index=True)
        return commentsDf
