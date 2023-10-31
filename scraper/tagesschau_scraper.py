import calendar
import os.path
import time

import pandas as pd
from selenium.webdriver.common.by import By

from scraper_bs4.scraper_interface import InformalScraperInterface
from utils import *


class TagesschauScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))
    waitTime = scraperConfig["waitTime"]

    def commentSectionExists(self, driver):
        commentSectionXpath = "//section[@id='node-story-comment']"
        commentSection = driver.find_elements(By.XPATH, commentSectionXpath)
        commentSectionExists = len(commentSection) > 0
        if commentSectionExists:
            return True
        else:
            return False

    def openCommentSection(self, driver):
        return

    def showAllComments(self, driver):
        return

    def showNewLevel0Comments(self, driver, date):
        return

    def getCommentDate(self, comment):
        timestampXpath = ".//time"
        timestamp = comment.find_element(By.XPATH, timestampXpath).get_attribute("datetime")
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z"))  # 2023-06-25T19:49:31+0200
        return timestampEpoch

    def createCommentText(self, commentTextParagraphs):
        commentText = ""
        for commentTextParagraph in commentTextParagraphs:
            commentText += commentTextParagraph.get_attribute(
                "textContent") + "\n"  # .text not working for some reason : https://stackoverflow.com/questions/39608637/selenium-text-not-working
        commentText = commentText[:-1]  # remove last linebreak
        return commentText

    def createCommentDf(self, comment, date):
        isResponseComment = "comment--answer" in comment.get_attribute("class")
        parentId = None
        if isResponseComment:
            parentLink = comment.find_elements(By.XPATH, ".//div[@class='comment__parent_link']/a")
            # split id from /id/169579/bundeszentrale-fuer-politische-bildung-afd-erfolg-ist-mehr-als-protest/comment/5132404#comment-5132404
            href = parentLink[0].get_attribute("href")
            parentId = href.rsplit("#", 1)[-1]  # #comment-65742485 remove "#"

        commentId = comment.get_attribute("id")
        userNameXpath = ".//span[@class='username']"
        userName = comment.find_element(By.XPATH, userNameXpath)
        userName = userName.get_attribute(
            "textContent")  # .text not working for some reason : https://stackoverflow.com/questions/39608637/selenium-text-not-working
        timestampEpoch = self.getCommentDate(comment)
        isNewComment = self.getCommentDate(comment) > date
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        updateDeletedInfo = self.scraperConfig["updateDeletedInfo"] == 1

        if isNewComment or scrapeCommentResponses or updateDeletedInfo:
            deleted = 0
            if userName == "Account gelöscht":
                deleted = 1
            commentContent = comment.find_element(By.XPATH, ".//div[@class='comment__content']")
            commentTextParagraphs = commentContent.find_elements(By.XPATH, ".//p")
            commentText = self.createCommentText(commentTextParagraphs)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": None, "downvotes": None, "loves": None,
                                        "likes": None,
                                        "stars": None, "hearts": None,
                                        "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        return newComment

    def scrapeComments(self, driver, date, pageSource):
        commentsDf = pd.DataFrame(
            columns=["cid", "parentid", "username", "comment", "timestamp", "deleted", "upvotes", "downvotes", "loves",
                     "likes", "stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"])
        commentsXpath = "//article[contains(@id, 'comment') and contains(@class, 'comment')]"
        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if not scrapeCommentResponses:
            commentsXpath = "//article[contains(@id, 'comment') and contains(@class, 'comment__main')]"

        atLeastOneRun = True  # while loop has to be executed once, to ensure that comment sites with only one page are scraped
        nextCommentPageXpath = "//a[@title='Zur nächsten Seite' and @rel='next']"
        nextCommentPageExists = len(driver.find_elements(By.XPATH, nextCommentPageXpath)) > 0
        while atLeastOneRun or nextCommentPageExists:
            if not atLeastOneRun:  # if we are not in the first run loop run we don't want to scrape the first comment page, so we have to open the next one
                nextCommentPageButton = driver.find_element(By.XPATH, nextCommentPageXpath)
                driver.execute_script("arguments[0].click()", nextCommentPageButton)
                time.sleep(self.waitTime)
            atLeastOneRun = False

            if scrapeCommentResponses:
                self.showAllComments(driver)
            comments = driver.find_elements(By.XPATH, commentsXpath)
            newCommentOnThisPage = self.getCommentDate(
                comments[-1]) > date  # comments in asceding order, check if date of last comment is greater than date
            if newCommentOnThisPage or scrapeCommentResponses:
                for comment in comments:
                    newComment = self.createCommentDf(comment, date)
                    commentsDf = commentsDf._append(newComment, ignore_index=True)

            nextCommentPageExists = len(driver.find_elements(By.XPATH, nextCommentPageXpath)) > 0

        return commentsDf
