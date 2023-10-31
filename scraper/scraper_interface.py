from pandas import DataFrame


class InformalScraperInterface():
    def acceptCookies(driver):
        """
        Accepts Spiegel Online Cookie Popup - Not needed anymore, cookie banners are now taken care of by Plugin
        :param driver:
        :return:
        """
        pass

    def commentSectionExists(self, driver) -> bool:
        """
        Checks whether a scrapable comment section exists or not.
        :param driver:
        :return:
        """
        pass

    def openCommentSection(self, driver):
        """
        Opens the comment section (and accesses comment section iframe) of an article to gain access to the comments.
        :param driver:
        :return:
        """
        pass

    def showAllComments(self, driver):
        """
        Shows all comments.
        :param driver:
        :return:
        """
        pass

    def showNewLevel0Comments(self, driver, date):
        """
        Shows all level0 comments that were published after a specific date.
        :param driver:
        :param date:
        :return:
        """
        pass

    def getCommentDate(self, comment) -> int:
        """
        Extracts (and converts) the timestamp of the time a comment was created.
        :param comment:
        :return:
        """
        pass

    def createCommentText(self, commentTextSpans) -> str:
        """
        Comment Text is often stored within multiple paragraphs or spans. Here those paragraphs / spans are joined together
         to produce one string that represents the comment text.
        :param commentTextSpans:
        :return:
        """
        pass

    def createCommentDf(self, commentElement, date) -> DataFrame:
        """
        Creates a DataFrame containing a comment.
        :param commentElement:
        :param date:
        :return:
        """
        pass

    def scrapeComments(self, driver, date) -> DataFrame:
        """
        Scrapes all (Level0) comments that were published after a specific date and stores them in a DataFrame.
        :param driver:
        :param date:
        :return:
        """
        pass
