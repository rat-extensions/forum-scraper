import calendar
import os.path
import time

import pandas as pd
from selenium.webdriver.common.by import By

from scraper_bs4.scraper_interface import InformalScraperInterface
from utils import *


class ZeitScraper(InformalScraperInterface):
    scraperConfig = fileToDictionary(os.path.join(os.path.dirname(__file__), os.path.pardir, "config_scraper.ini"))
    waitTime = scraperConfig["waitTime"]

    async def commentSectionExists(self, driver):
        commentSectionXpath = "//div[@class='comments__body']"
        commentSection = driver.find_elements(By.XPATH,
                                              commentSectionXpath)
        commentSectionExists = len(commentSection) > 0
        if commentSectionExists:
            return True
        else:
            return False

    def openCommentSection(self, driver):
        # Open comment section for article and switch to comment iframe
        showAllCommentsButtonXpath = "//button[contains(@class,'comments__sort-button') and @value='newest']"
        showCommentsButton = driver.find_element(By.XPATH, showAllCommentsButtonXpath)
        if showCommentsButton:
            driver.execute_script("arguments[0].click()", showCommentsButton)

    def showAllComments(self, driver):
        showMoreButtonXpath = "//button[(contains(@class,'svelte-13pupk0') and @data-ct-ck4='thread_loadmore_click')]" \
                              "| //div[@class='comment__links']//button[(@class='comment__link' and @data-ct-ck4='comment_hide_answers')]" \
                              "| //button[@class='comment__link' and @data-ct-ck4='comment_show_more_answers']"

        showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreButtonXpath)
        if len(showMoreCommentsButtons) > 0:
            button = showMoreCommentsButtons[0]
            driver.execute_script("arguments[0].click()", button)
            time.sleep(1)

        lastHeight = driver.execute_script("return document.body.scrollHeight")
        isEndOfPage = False
        showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreButtonXpath)
        while (len(showMoreCommentsButtons) > 0) and (not isEndOfPage):
            button = showMoreCommentsButtons[0]
            driver.execute_script("arguments[0].click()", button)
            time.sleep(1)
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")  # Scrolling to the bottom makes the page show more comments
            time.sleep(1)
            newHeight = driver.execute_script("return document.body.scrollHeight")
            if lastHeight == newHeight:
                isEndOfPage = True
            else:
                lastHeight = newHeight
            showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreButtonXpath)

    def showNewLevel0Comments(self, driver, date):
        showMoreCommentsButtonXpath = "//button[contains(@class,'svelte-13pupk0') and @data-ct-ck4='thread_loadmore_click']"
        commentLevelOXpath = "//article[@class='comment' and contains(@data-ct-ck5, 'comment_root')]"
        commentsLevel0 = driver.find_elements(By.XPATH,
                                              commentLevelOXpath)

        # More Comments are loaded by scrolling downwards
        showMoreCommentsButtons = driver.find_elements(By.XPATH, showMoreCommentsButtonXpath)
        onlyNewLevel0CommentsVisible = (self.getCommentDateWE(commentsLevel0[-1]) > date)
        if onlyNewLevel0CommentsVisible and (
                len(showMoreCommentsButtons) > 0):
            button = showMoreCommentsButtons[0]
            driver.execute_script("arguments[0].click()", button)
        lastHeight = driver.execute_script("return document.body.scrollHeight")
        isEndOfPage = False
        onlyNewLevel0CommentsVisible = (self.getCommentDateWE(commentsLevel0[-1]) > date)
        while onlyNewLevel0CommentsVisible and not isEndOfPage:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            newHeight = driver.execute_script("return document.body.scrollHeight")
            if lastHeight == newHeight:
                isEndOfPage = True
            else:
                lastHeight = newHeight
            commentsLevel0 = driver.find_elements(By.XPATH,
                                                  commentLevelOXpath)
            onlyNewLevel0CommentsVisible = (self.getCommentDateWE(commentsLevel0[-1]) > date)

    def getCommentDateWE(self, comment):
        timestampXpath = ".//time[@class='comment__date']"
        timestamp = comment.find_element(By.XPATH, timestampXpath).get_attribute("datetime")
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ"))  # 2023-06-21T07:34:41.994Z
        return timestampEpoch

    def getCommentDate(self, comment):
        timestamp = comment.find("time", class_="comment__date")["datetime"]
        timestampEpoch = calendar.timegm(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ"))  # 2023-06-21T07:34:41.994Z
        return timestampEpoch

    def createCommentText(self, commentTextParagraphs):
        commentText = ""
        for commentTextParagraph in commentTextParagraphs:
            commentText += commentTextParagraph.getText() + "\n"
        commentText = commentText[:-1]  # remove last linebreak
        return commentText

    def createCommentDf(self, comment, date):
        newComment = None
        reactions = pd.DataFrame(
            [{"stars": None, "hearts": None, "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
        classes = " ".join(comment["class"])
        isResponseComment = classes == "comment reply"
        parentId = None
        if isResponseComment:
            parentContent = comment.select("a[class='parent__content'][data-ct-ck4='comment_parent_link']")
            isResponseToResponse = len(parentContent) > 0
            # If the comment is a response to another comment response we can find a parent reference and the content, id etc. to which it refers
            if isResponseToResponse:
                # split id from https://www.zeit.de/gesellschaft/zeitgeschehen/2023-06/alfons-schuhbeck-steuerhinterziehung-bundesgerichtshof#cid-65744873
                href = parentContent[0]["href"]
                parentId = href.rsplit("#", 1)[-1]  # #cid-65742485 remove "#"
            else:
                parentComment = comment.parent.parent.find("article")
                parentId = parentComment["id"]

        commentId = comment["id"]
        userName = comment.select("a[data-ct-ck4='comment_username_click']")
        if len(userName) == 0:  # 2ter Path nötig, da es Nutzer gibt deren Profil man nicht durch Anklicken aufrufen kann, UN ist dann in h4
            userName = comment.select("h4[class='comment__name']")
        userName = userName[0].getText()
        timestampEpoch = self.getCommentDate(comment)
        isDeletedComment = len(
            comment.find_all("em", class_="moderation")) > 0  # By.XPATH, ".//em[@class='moderation']")) > 0
        isNewComment = timestampEpoch > date
        updateDeletedInfo = self.scraperConfig["updateDeletedInfo"] == 1
        if (isNewComment or updateDeletedInfo) and isDeletedComment:
            deletedComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                            "comment": None, "timestamp": timestampEpoch, "deleted": 1,
                                            "upvotes": None, "downvotes": None, "loves": None, "likes": None,
                                            "stars": None, "hearts": None,
                                            "smiles": None, "frowns": None, "eyebrows": None, "astonisheds": None}])
            return deletedComment

        scrapeUpdateReactions = self.scraperConfig["scrapeAndUpdateReactions"] == 1
        if isNewComment or scrapeUpdateReactions:
            deleted = 0
            if scrapeUpdateReactions:
                reactions = pd.DataFrame(
                    [{"stars": 0, "hearts": 0, "smiles": 0, "frowns": 0, "eyebrows": 0, "astonisheds": 0}], dtype=int)
                commentReactions = comment.find_all("button", class_="comment__reaction")[
                                   :-1]  # slice to remove addReaction button that is also found
                for commentReaction in commentReactions:
                    reactionType = commentReaction["value"]
                    reactionCount = commentReaction.getText()[2:]  # slice to remove reaction icon
                    reactions[reactionType + "s"] = reactionCount

            commentContent = comment.find("div", class_="comment__body comment__user-input")
            commentTextParagraphs = commentContent.find_all("p")
            commentText = self.createCommentText(commentTextParagraphs)

            newComment = pd.DataFrame([{"cid": commentId, "parentid": parentId, "username": userName,
                                        "comment": commentText, "timestamp": timestampEpoch,
                                        "deleted": deleted, "upvotes": None, "downvotes": None, "loves": None,
                                        "likes": None}])
            newComment = pd.concat([newComment, reactions], axis=1, join='inner')
            if scrapeUpdateReactions:
                columns = ["stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"]
                newComment[columns] = newComment[columns].astype(
                    int)  # convert floats (that emerged due to concat) to int
        return newComment

    def scrapeComments(self, driver, date, soup):
        commentsDf = pd.DataFrame(
            columns=["cid", "parentid", "username", "comment", "timestamp", "deleted", "upvotes", "downvotes", "loves",
                     "likes", "stars", "hearts", "smiles", "frowns", "eyebrows", "astonisheds"])
        commentSelect = "article[class*='comment'][data-ct-ck5*='comment']"

        scrapeCommentResponses = self.scraperConfig["scrapeResponses"] == 1
        if not scrapeCommentResponses:
            commentSelect = "article[class*='comment'][data-ct-ck5*='comment_root']"
        comments = soup.select(commentSelect)

        for comment in comments:
            newComment = self.createCommentDf(comment, date)
            commentsDf = commentsDf._append(newComment, ignore_index=True)
        return commentsDf
