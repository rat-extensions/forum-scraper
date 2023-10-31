import threading
from subprocess import call

"""Source: https://github.com/rat-software/rat-software/tree/main/sources/app with changes"""


def scraping():
    call(["python", "scraping_job.py"])


process = threading.Thread(target=scraping)
process.start()
