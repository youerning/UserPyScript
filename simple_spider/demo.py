from Spider import spider

if __name__ == "__main__":
    startURL = "http://baike.baidu.com/item/python"
    crawler = spider(startURL)
    crawler.crawl(size=10)

