import calendar
import os.path
import time

import pandas as pd
from selenium.common import ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scraper_bs4.scraper_interface import InformalScraperInterface
from utils import *


class SpiegelScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))
    waitTime = scraperConfig["waitTime"]

    async def commentSectionExists(self, driver):
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
        commentSectionButton = driver.find_element(By.XPATH, commentSectionButtonXpath)
        driver.execute_script("arguments[0].click()", commentSectionButton)
        iframeCommentSectionXpath = "//*[starts-with(@id,'_0.') and contains(@id,'_iframe')]"
        iframeComments = WebDriverWait(driver, self.waitTime).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframeCommentSectionXpath))
        )
        # show All Comments comments and not only recommended comments
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
        onlyNewLevel0CommentsVisible = self.getCommentDateWE(commentsLevel0[-1]) > date
        while (onlyNewLevel0CommentsVisible) and (len(showMoreCommentsButtons) > 0):
            button = showMoreCommentsButtons[0]
            driver.execute_script("arguments[0].click()", button)
            time.sleep(1)
            commentsLevel0 = driver.find_elements(By.XPATH,
                                                  commentLevelOXpath)
            onlyNewLevel0CommentsVisible = self.getCommentDateWE(commentsLevel0[-1]) > date
            showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreCommentsButtonXpath)

    def getCommentDateWE(self, comment):
        timestampXpath = ".//span[@class='CommentTimestamp__timestamp___2Ejbf talk-comment-timestamp TimeAgo__timeago___3aHze talk-comment-timeago']"
        timestamp = comment.find_element(By.XPATH, timestampXpath).get_attribute("title")
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%m/%d/%Y, %I:%M:%S %p"))
        return timestampEpoch

    def getCommentDate(self, comment):
        timestamp = comment.find("span",
                                 class_="CommentTimestamp__timestamp___2Ejbf talk-comment-timestamp TimeAgo__timeago___3aHze talk-comment-timeago")[
            "title"]
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%m/%d/%Y, %I:%M:%S %p"))
        return timestampEpoch

    def createCommentText(self, commentTextSpans):
        commentText = ""
        for commentTextSpan in commentTextSpans:
            commentText += commentTextSpan.getText() + "\n"
        commentText = commentText[:-1]  # remove last linebreak
        return commentText

    def createCommentDf(self, commentWrapper, date):
        newComment = None
        classesJoin = " ".join(commentWrapper["class"])
        commentLevel = int(classesJoin.split("talk-stream-comment-wrapper talk-stream-comment-wrapper-level-", 1)[1][0])
        commentId = commentWrapper["id"]
        parentId = None
        if commentLevel != 0:  # Level0 comments have no parent
            parentComment = commentWrapper.find_parent(lambda
                                                           tag: tag.name == "div" and "talk-stream-comment-wrapper talk-stream-comment-wrapper-level" in " ".join(
                tag.get("class", [])))
            parentId = parentComment["id"]
        commentSelector = f"div[class*='talk-stream-comment talk-stream-comment-level-{commentLevel}']"
        comments = commentWrapper.select(commentSelector)
        isDeletedComment = len(comments) == 0
        if isDeletedComment:
            deletedComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": None, "comment": None,
                                            "timestamp": None, "deleted": 1,
                                            "upvotes": None, "downvotes": None, "loves": None, "likes": None,
                                            "stars": None,
                                            "hearts": None,
                                            "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
            return deletedComment
        else:
            comment = comments[0]

        timestampEpoch = self.getCommentDate(comment)
        isNewComment = timestampEpoch > date
        scrapeUpdateReactions = self.scraperConfig["scrapeAndUpdateReactions"] == 1
        if isNewComment or scrapeUpdateReactions:
            deleted = 0
            userName = comment.find("span", class_="AuthorName__name___3O4jF").getText()
            upvotes = None
            downvotes = None
            if scrapeUpdateReactions:
                upvotes = comment.find("span", class_="talk-plugin-upvote-count").getText()
                if upvotes == "":
                    upvotes = 0
                downvotes = comment.find("span", class_="talk-plugin-downvote-count").getText()
                if downvotes == "":
                    downvotes = 0

            commentContent = comment.find("div", class_="talk-stream-comment-content talk-slot-comment-content")
            commentTextSpans = commentContent.find_all("span", class_="Linkify")
            commentText = self.createCommentText(commentTextSpans)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": upvotes, "downvotes": downvotes, "loves": None,
                                        "likes": None,
                                        "stars": None, "hearts": None,
                                        "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        return newComment

    def scrapeComments(self, driver, date, soup):
        commentsDf = pd.DataFrame(
            columns=["cid", "parentid", "username", "comment", "timestamp", "deleted", "upvotes", "downvotes", "loves",
                     "likes", "stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"])
        commentsWrapperSelect = "div[class*='talk-stream-comment-wrapper talk-stream-comment-wrapper-level']"
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if not scrapeCommentResponses:
            commentsWrapperSelect = "div[class*='talk-stream-comment-wrapper talk-stream-comment-wrapper-level-0']"
        commentWrapper = soup.select(commentsWrapperSelect)

        for cw in commentWrapper:
            newComment = self.createCommentDf(cw, date)
            commentsDf = commentsDf._append(newComment, ignore_index=True)
        return commentsDf
