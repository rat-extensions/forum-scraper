import calendar
import os
import time

import pandas as pd
from selenium.webdriver.common.by import By

from scraper.scraper_interface import InformalScraperInterface
from utils import *


class TAZScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))

    def commentSectionExists(self, driver):
        commentSectionXpath = "//div[@class='even sect sect_commentlinks style_commentlinks '] " \
                              "| //p[@class='label' and contains(text(), 'Ihren Kommentar hier eingeben')]" \
                              "| //p[@class='label' and contains(text(), 'Geben Sie Ihren Kommentar hier ein')]"
        commentSection = driver.find_elements(By.XPATH,
                                              commentSectionXpath)
        commentSectionExists = len(commentSection) > 0
        if commentSectionExists:
            return True
        else:
            return False

    def openCommentSection(self, driver):
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")  # Scrolling to the bottom makes the page show all comments

    def showAllComments(self, driver):
        return

    def showNewLevel0Comments(self, driver, date):
        return

    def getCommentDate(self, comment):
        timestampXpath = ".//time"
        timestamp = comment.find_element(By.XPATH, timestampXpath).get_attribute("datetime")
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z"))  # 2023-06-29T09:30:34+02:00
        return timestampEpoch

    def createCommentText(self, commentTextParagraphs):
        commentText = ""
        for commentTextParagraph in commentTextParagraphs:
            commentText += commentTextParagraph.text + "\n"
        commentText = commentText[:-1]  # remove last linebreak
        return commentText

    def createCommentDf(self, comment, date):
        parentClass = comment.find_element(By.XPATH, "./..").get_attribute("class")
        isResponseComment = parentClass == "thread"
        parentId = None
        if isResponseComment:
            parent = comment.find_element(By.XPATH, "./../..")
            parentId = parent.get_attribute("id")

        commentId = comment.get_attribute("id")
        userNameXpath = ".//a[@class='author person']/h4"
        userName = comment.find_element(By.XPATH, userNameXpath)
        userName = userName.text
        timestampEpoch = self.getCommentDate(comment)
        isDeletedComment = len(comment.find_elements(By.XPATH, ".//em[@class='moderation']")) > 0
        isNewComment = self.getCommentDate(comment) > date
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        updateDeletedInfo = self.scraperConfig["updateDeletedInfo"] == 1
        if (isNewComment or scrapeCommentResponses or updateDeletedInfo) and isDeletedComment:
            deletedComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                            "comment": None, "timestamp": timestampEpoch, "deleted": 1,
                                            "upvotes": None, "downvotes": None, "loves": None, "likes": None,
                                            "stars": None, "hearts": None,
                                            "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
            return deletedComment

        if isNewComment or scrapeCommentResponses:
            deleted = 0

            commentContent = comment.find_element(By.XPATH, ".//div[@class='objlink nolead' and @role='link']")
            commentTextParagraphs = commentContent.find_elements(By.XPATH, ".//p")
            commentText = self.createCommentText(commentTextParagraphs)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": None, "downvotes": None, "loves": None,
                                        "likes": None,
                                        "stars": None, "hearts": None,
                                        "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        return newComment

    def scrapeComments(self, driver, date):
        """Scrape all (Level0) comments that were published after a specific date. AND OR Scrape """
        commentsDf = pd.DataFrame(
            columns=["cid", "parentid", "username", "comment", "timestamp", "deleted", "upvotes", "downvotes", "loves",
                     "likes",
                     "stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"])
        commentsXpath = "//li[contains(@id, 'bb_message') and contains(@class, 'member')]"
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if not scrapeCommentResponses:
            commentsXpath = "//ul[@class='sectbody   directory' and @role='directory']/li[contains(@id, 'bb_message') and contains(@class, 'member')]"
        comments = driver.find_elements(By.XPATH, commentsXpath)

        for comment in comments:
            newComment = self.createCommentDf(comment, date)
            commentsDf = commentsDf._append(newComment, ignore_index=True)
        return commentsDf
