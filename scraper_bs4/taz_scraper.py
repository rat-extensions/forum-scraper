import calendar
import os
import time

import pandas as pd
from selenium.webdriver.common.by import By

from scraper_bs4.scraper_interface import InformalScraperInterface
from utils import *


class TAZScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))

    async def commentSectionExists(self, driver):
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
        timestamp = comment.find("time")["datetime"]
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z"))  # 2023-06-29T09:30:34+02:00
        return timestampEpoch

    def createCommentText(self, commentTextParagraphs):
        commentText = ""
        for commentTextParagraph in commentTextParagraphs:
            commentText += commentTextParagraph.getText() + "\n"
        commentText = commentText[:-1]  # remove last linebreak
        return commentText

    def createCommentDf(self, comment, date):
        newComment = None
        parentClass = " ".join(comment.parent["class"])
        isResponseComment = parentClass == "thread"
        parentId = None
        if isResponseComment:
            parentComment = comment.parent.parent
            parentId = parentComment["id"]

        commentId = comment["id"]
        userName = comment.find("a", class_="author person").find("h4")
        userName = userName.getText()
        timestampEpoch = self.getCommentDate(comment)
        isNewComment = self.getCommentDate(comment) > date
        if isNewComment:
            deleted = 0

            commentContent = comment.find("div", {"class": "objlink nolead", "role": 'link'})
            commentTextParagraphs = commentContent.find_all("p")
            commentText = self.createCommentText(commentTextParagraphs)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": None, "downvotes": None, "loves": None,
                                        "likes": None,
                                        "stars": None, "hearts": None,
                                        "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        return newComment

    def scrapeComments(self, driver, date, soup):
        commentsDf = pd.DataFrame(
            columns=["cid", "parentid", "username", "comment", "timestamp", "deleted", "upvotes", "downvotes", "loves",
                     "likes",
                     "stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"])
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if not scrapeCommentResponses:
            commentList = soup.find("ul", {"class": "sectbody directory", "role": "directory"})
            comments = commentList.find_all("li", {"class": "member"}, recursive=False)
        else:
            comments = soup.select("li[id*='bb_message']")

        for comment in comments:
            newComment = self.createCommentDf(comment, date)
            commentsDf = commentsDf._append(newComment, ignore_index=True)
        return commentsDf
