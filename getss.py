#coding:utf8
#get the free shodowsocks account and save the information to qr png file
from base64 import b64encode
from bs4 import BeautifulSoup
import qrcode
import requests

ssURL = "http://www.ishadowsocks.org/"
page = requests.get(ssURL)
soup = BeautifulSoup(page.content,"lxml")

authALL = soup.findAll(class_="col-lg-4 text-center")
sourceLis = []
destLis = []

for server in authALL[:3]:
    lis = []
    for info in server.children:
        if info != "\n":
                #print info.string
                lis.append(info.string.split(":")[1])
                if info.string.split(":")[1] == "aes-256-cfb":
                    break
    #authURL = ":".join(lis)
    authURL = lis[3] + ":" + lis[2] + "@" + lis[0] + ":" + lis[1]
    sourceLis.append(authURL)
    destLis.append("ss://" + b64encode(authURL))

print sourceLis
print destLis

for i, j in zip(destLis,range(len(destLis))):
    img = qrcode.make(i)
    img.save(str(j) + ".png")
