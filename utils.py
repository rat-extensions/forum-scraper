import csv
import json


def fileToDictionary(path):
    with open(path, encoding="UTF-8") as file:
        dictionary = json.load(file)
    return dictionary

def csvFileToList(path):
    """
    Reads in a csv file and returns it as a list. The header line of the CSV file is removed from the list.
    :param path:
    :return:
    """
    with open(path, "r") as file:
        fileList = list(csv.reader(file, delimiter=","))
    fileList.pop(0) #remove header line
    return fileList


import re
from log.logger import log
from scraper_bs4.faz_scraper import FAZScraper
from scraper_bs4.focus_scraper import FocusScraper
from scraper_bs4.spiegel_scraper import SpiegelScraper
from scraper_bs4.sz_scraper import SZScraper
from scraper_bs4.tagesschau_scraper import TagesschauScraper
from scraper_bs4.taz_scraper import TAZScraper
from scraper_bs4.zeit_scraper import ZeitScraper


def determineNewspageUrl(newspageUrls, articleUrl):
    """
    Recieves an url and if possible raturns the newspage url.
    :param newspagesDf:
    :param articleUrl:
    :return:
    """
    rootDomainRegex = r"(http(s)?://(www\.)?.*\.(de|com|net)/)"  # http(s) Root Url with or without www and de/com/net suffix
    match = re.match(rootDomainRegex, articleUrl, re.MULTILINE | re.IGNORECASE)
    if match:
        rootDomain = match.groups()
        url = rootDomain[0]
        if url in newspageUrls:
            return url
    return None


def determineScraper(newspage):
    """
    Recieves an url (should be a newspage) and returns the corresponding scraper.
    :param newspage:
    :return:
    """
    match newspage:
        case "https://www.faz.net/":
            scraper = FAZScraper()
        case "https://www.focus.de/":
            scraper = FocusScraper()
        case "https://www.sueddeutsche.de/":
            scraper = SZScraper()
        case "https://www.spiegel.de/":
            scraper = SpiegelScraper()
        case "https://meta.tagesschau.de/":
            scraper = TagesschauScraper()
        case "https://taz.de/":
            scraper = TAZScraper()
        case "https://www.zeit.de/":
            scraper = ZeitScraper()
        case _:
            scraper = None
    return scraper


def removeDuplicates(df):
    """
    Removes duplicates from a dataframe.
    :param df:
    :return:
    """
    duplicates = df[df.duplicated()]
    duplicatesExist = len(duplicates.index) > 0
    if duplicatesExist:
        log("Duplicates found: " + duplicates.to_string())
        df = df.drop_duplicates()
    return df
