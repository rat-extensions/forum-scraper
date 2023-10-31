import calendar
import os
import time

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scraper_bs4.scraper_interface import InformalScraperInterface
from utils import *


class FAZScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))
    waitTime = scraperConfig["waitTime"]

    async def commentSectionExists(self, driver):
        # Comment section (if possible) has to be opened to check whether the comment section is only accessible to FAZ+ users.
        commentSectionButtonXpath = "//a[@class='ctn-PageFunctions_Link js-comment-link' and @title='Lesermeinungen' and @track-subposition='Abbinder']"
        commentSectionButton = driver.find_elements(By.XPATH,
                                                    commentSectionButtonXpath)  # Button to open the comment section only exist if the commentsection is enabled
        commentSectionExists = len(commentSectionButton) > 0
        if commentSectionExists:
            driver.execute_script("arguments[0].click()", commentSectionButton[0])
            var = driver.find_elements(By.XPATH,
                                       "//p[@class='pop-Message_Description' and contains(text(), 'Die Diskussion in diesem Artikel ist exklusiv für Abonnenten.')]")
            commentSectionOnlyFAZPremium = len(var) > 0
            if commentSectionOnlyFAZPremium:
                return False
            commentSectionCloseButtonXpath = "//button[@class='cmt-Overlay_Close js-cmt-close']"
            commentSectionCloseButton = WebDriverWait(driver, self.waitTime).until(
                EC.presence_of_element_located((By.XPATH, commentSectionCloseButtonXpath)))
            driver.execute_script("arguments[0].click()", commentSectionCloseButton)
            return True
        else:
            return False

    def openCommentSection(self, driver):
        # Open comment section for article and switch to comment iframe
        commentSectionButtonXpath = "//a[@class='ctn-PageFunctions_Link js-comment-link' and @title='Lesermeinungen' and @track-subposition='Einleitung']"
        commentSectionButton = driver.find_element(By.XPATH, commentSectionButtonXpath)
        driver.execute_script("arguments[0].click()", commentSectionButton)
        iframeCommentSectionXpath = "//*[starts-with(@id,'_0.') and contains(@id,'_iframe')]"
        iframeComments = WebDriverWait(driver, self.waitTime).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframeCommentSectionXpath))
        )

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
        commentsLevel0 = driver.find_elements(By.XPATH,
                                              commentLevelOXpath)
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
            timestampEpoch = self.getCommentDate(comment)
            upvotes = None
            downvotes = None
            loves = None
            if scrapeUpdateReactions:
                upvotes = comment.find("span", class_="talk-plugin-upvote-count").getText()
                if upvotes == "":
                    upvotes = 0
                downvotes = comment.find("span", class_="talk-plugin-downvote-count").getText()
                if downvotes == "":
                    downvotes = 0
                loves = comment.find("span", class_="talk-plugin-love-count").getText()
                if loves == "":
                    loves = 0

            commentContent = comment.find("div", class_="talk-stream-comment-content talk-slot-comment-content")
            commentTextSpans = commentContent.find_all("span", class_="Linkify")
            commentText = self.createCommentText(commentTextSpans)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": upvotes, "downvotes": downvotes, "loves": loves,
                                        "likes": None,
                                        "stars": None, "hearts": None,
                                        "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        return newComment

    def scrapeComments(self, driver, date, soup):
        commentsDf = pd.DataFrame(
            columns=["cid", "parentid", "username", "comment", "timestamp", "deleted", "upvotes", "downvotes", "loves",
                     "likes",
                     "stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"])
        commentsWrapperSelect = "div[class*='talk-stream-comment-wrapper talk-stream-comment-wrapper-level']"
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if not scrapeCommentResponses:
            commentsWrapperSelect = "div[class*='talk-stream-comment-wrapper talk-stream-comment-wrapper-level-0']"
        commentWrapper = soup.select(commentsWrapperSelect)

        for cw in commentWrapper:
            newComment = self.createCommentDf(cw, date)
            commentsDf = commentsDf._append(newComment, ignore_index=True)
        return commentsDf
