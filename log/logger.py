from datetime import datetime


def log(log):
    timestamp = datetime.now()
    with open("./log/log.txt", "a") as file:
        file.write(str(timestamp) + ": " + log + "\n")
