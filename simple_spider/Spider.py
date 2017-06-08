#coding:utf8
import Handler

class spider(object):
    """docstring for spider"""
    def __init__(self, url):
        self.url = [url]
        self.urlManager = Handler.urlManager()
        self.output = Handler.Output()
        self.download = Handler.Download()
        self.parser = Handler.Parser()

    def crawl(self, size=100):
        count = 0
        self.urlManager.add(self.url)
        while len(self.urlManager.new_urls):
            try:
                url = self.urlManager.get()
                cont = self.download.download(url)
                urls, data = self.parser.parser(url, cont)
                self.urlManager.add(urls)
                self.output.add(data)
                if count > size:
                    break
                count += 1
                print "url: %s crawled" % url
            except Exception as e:
                print "crawl faild"
                print e

        self.output.save()
