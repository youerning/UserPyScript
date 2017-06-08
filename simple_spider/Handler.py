#coding: utf8
from bs4 import BeautifulSoup
import requests
import re
import urlparse

class urlManager(object):
    def __init__(self):
        self.new_urls = set()
        self.old_urls = set()

    def add(self, urls):
        if len(urls) == 0 :
            return

        # fil = lambda x: x not in self.new_urls and not in old_urls
        for url in urls:
            if url not in self.new_urls and url not in self.old_urls:
                self.new_urls.add(url)
    def get(self):
        url = self.new_urls.pop()
        self.old_urls.add(url)

        return url


class Download(object):
    def download(self, url):
        resp = requests.get(url)
        if resp.ok:
            cont = resp.content
            return cont


class Parser(object):
    def parser(self, url, cont):
        data = {}
        soup = BeautifulSoup(cont, "html.parser")
        urls = []

        title = soup.find("h1").text
        summary = soup.find("div", class_="lemma-summary").text
        data["url"] = url
        data["title"] = title
        data["summary"] = summary

        aTag = soup.find_all("a", href=re.compile(r"/item/.*"))
        for a in aTag:
            link = a["href"]
            link = urlparse.urljoin(url, link)
            # print link
            urls.append(link)

        return urls, data

class Output(object):
    def __init__(self):
        self.ret = []

    def add(self, data):
        self.ret.append(data)

    def save(self):
        head = "<tr><th>url</th><th>Title</th><th>Summary</th></tr>"
        row = "<tr><td>'%s'</td><td>'%s'</td><td>'%s'</td></tr>"

        with open("output.html", "w") as wf:
            wf.write("<table>")
            wf.write(head)
            for i in self.ret:
                # print row % (i["url"].encode("utf8"), i["title"].encode("utf8"), i["summary"].encode("utf8"))
                r = row % (i["url"].encode("utf8"), i["title"].encode("utf8"), i["summary"].encode("utf8"))
                wf.write(r)
            wf.write("</table>")
