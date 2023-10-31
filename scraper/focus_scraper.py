import calendar
import os.path
import time

import pandas as pd
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from scraper.scraper_interface import InformalScraperInterface
from utils import *


class FocusScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))
    waitTime = scraperConfig["waitTime"]

    def commentSectionExists(self, driver):
        commentSectionButtonXpath = "//button[@class='comments-count-button comments-load bluebutton' and contains(text(), 'Kommentare öffnen')]"
        commentSectionButton = driver.find_elements(By.XPATH,
                                                    commentSectionButtonXpath)  # Button to open the comment section only exist if the commentsection is enabled
        commentSectionExists = len(commentSectionButton) > 0
        if commentSectionExists:
            return True
        else:
            return False

    def openCommentSection(self, driver):
        # Open comment section for article and switch to comment iframe
        commentSectionButtonXpath = "//button[@class='comments-count-button comments-load bluebutton' and contains(text(), 'Kommentare öffnen')]"
        commentSectionButton = WebDriverWait(driver, self.waitTime).until(
            EC.element_to_be_clickable((By.XPATH, commentSectionButtonXpath)))
        driver.execute_script("arguments[0].click()", commentSectionButton)
        iframeCommentSectionXpath = "//iframe[@id='coral_community_iframe']"
        iframeComments = WebDriverWait(driver, self.waitTime).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, iframeCommentSectionXpath))
        )

    def showAllComments(self, driver):
        showMoreButtonXpath = "//button[contains(@class, 'talk-load-more-button')]"
        showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreButtonXpath)

        while len(showMoreCommentsButtons) > 0:
            button = showMoreCommentsButtons[0]
            driver.execute_script("arguments[0].click()", button)
            time.sleep(1)
            showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreButtonXpath)

    def showNewLevel0Comments(self, driver, date):
        showMoreCommentsButtonXpath = "//button[contains(@class,'talk-load-more-button') and contains(text(), 'Mehr Kommentare anzeigen')]"
        commentLevelOXpath = "//div[contains(@class, 'talk-stream-comment talk-stream-comment-level-0 Comment__comment___3_T6p Comment__commentLevel0___1B4Fw')]"
        commentsLevel0 = driver.find_elements(By.XPATH,
                                              commentLevelOXpath)

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
        commentLevel = int(commentWrapper.get_attribute("class").split(
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
            deletedComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": None,
                                            "comment": None, "timestamp": None,
                                            "deleted": 1, "upvotes": None, "downvotes": None, "loves": None,
                                            "likes": None, "stars": None, "hearts": None,
                                            "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
            return deletedComment

        isNewComment = self.getCommentDate(comment) > date
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if isNewComment or scrapeCommentResponses:
            deleted = 0
            userName = comment.find_element(By.XPATH, ".//span[@class='AuthorName__name___3O4jF']").text
            timestampEpoch = self.getCommentDate(comment)

            commentContent = comment.find_element(By.XPATH,
                                                  ".//div[@class='talk-stream-comment-content talk-slot-comment-content']")
            commentTextSpans = commentContent.find_elements(By.XPATH, ".//span[@class='Linkify']")
            commentText = self.createCommentText(commentTextSpans)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": None, "downvotes": None, "loves": None,
                                        "likes": None, "stars": None, "hearts": None,
                                        "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        return newComment

    def scrapeComments(self, driver, date):
        """Scrape all (Level0) comments that were published after a specific date. AND OR Scrape """
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
