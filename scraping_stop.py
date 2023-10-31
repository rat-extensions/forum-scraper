import time

from log.logger import log
from utils import fileToDictionary

"""Source: https://github.com/rat-software/rat-software/tree/main/sources/app with changes"""

log("Stop Scraper")

scraperConfig = fileToDictionary("config_scraper.ini")

import psutil

for proc in psutil.process_iter(attrs=['pid', 'name']):
    if 'python' in proc.info['name']:

        try:
            if "scraping_job.py" in proc.cmdline():
                proc.kill()
        except:
            pass

        try:
            if "main.py" in proc.cmdline():
                proc.kill()
        except:
            pass

    try:
        if "chrome" in proc.info['name']:
            proc.kill()
    except:
        pass

    try:
        if "chromedriver" in proc.info['name']:
            proc.kill()
    except:
        pass

time.sleep(30)

for proc in psutil.process_iter(attrs=['pid', 'name']):
    if 'python' in proc.info['name']:

        try:
            if "scraping_job.py" in proc.cmdline():
                proc.kill()
        except:
            pass

        try:
            if "main.py" in proc.cmdline():
                proc.kill()
        except:
            pass

    try:
        if "chrome" in proc.info['name']:
            proc.kill()
    except:
        pass

    try:
        if "chromedriver" in proc.info['name']:
            proc.kill()
    except:
        pass
