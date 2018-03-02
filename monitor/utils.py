#coding: utf-8
import sys
import smtplib
from functools import wraps
from email.mime.text import MIMEText
from configparser import ConfigParser

confile = "monitor.conf"

conf = ConfigParser()
conf.read(confile)

smtpServer = "smtp.163.com"
reciver = conf["mail"]["reciver"]
smtpUser = conf["mail"]["username"]
smtpPass = conf["mail"]["password"]
sender = smtpUser
# 126 mail server treat the message contain string "test" like Spam.
testMsg = "this is a email for 126 and for someone use the email script."


def cache(func):
    data = {}

    @wraps(func)
    def wrapper(*args):
        if args in data:
            return data[args]
        else:
            res = func(*args)
            data[args] = res
            return res
    return wrapper


def sendMail(subject, message):
    server = smtplib.SMTP()
    server.connect(smtpServer)
    # server.set_debuglevel(1)
    # server.ehlo()
    # server.starttls()
    # server.ehlo()
    server.login(smtpUser, smtpPass)
    # server.set_debuglevel(1)
    msg = MIMEText(message, "plain", "utf8")
    msg["Subject"] = subject
    msg["From"] = smtpUser
    msg["To"] = reciver
    server.sendmail(smtpUser, [reciver], msg.as_string())
    server.quit()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "-t":
        sendMail("monitor message for stock", testMsg)
    else:
        try:
            sendMail(*sys.argv[1:])
        except Exception as e:
            pass
