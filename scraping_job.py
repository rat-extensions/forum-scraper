import os
from datetime import datetime
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler

from utils import fileToDictionary

"""Source: https://github.com/rat-software/rat-software/tree/main/sources/app with changes"""


def job():
    os.system('python main.py')


if __name__ == '__main__':
    scraperConfig = fileToDictionary("config_scraper.ini")
    repeatEvery = int(scraperConfig["startScrapingJobEveryXHours"])

    scheduler = BackgroundScheduler()
    scheduler.add_job(job, "interval", hours=repeatEvery, next_run_time=datetime.now())
    scheduler.start()

    while True:
        sleep(1)
