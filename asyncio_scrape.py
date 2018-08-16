import asyncio
import aiomysql
import aiohttp
import re
from pyquery import PyQuery

stopping = False
start_url = "http://www.jobbole.com/"
waiting_url = []
seen_urls = set()
sem = asyncio.Semaphore(3)


async def fetch(url, session):
    async with sem:
            try:
                async with session.get(url) as resp:
                    # print("status: ", resp.status)
                    if resp.status in [200, 201]:
                        data = await resp.text()
                        return data
                    else:
                        pass
            except Exception as e:
                print(e)


def extract_url(html):
    urls = []
    pg = PyQuery(html)

    for link in pg.items("a"):
        url = link.attr("href")
        if url and url.startswith("http") and url not in seen_urls:
            urls.append(url)
            waiting_url.append(url)


async def init_urls(url, session):
    html = await fetch(url, session)
    seen_urls.add(url)
    extract_url(html)


async def article_handler(url, session, pool):
    html = await fetch(url, session)
    seen_urls.add(url)
    extract_url(html)
    pg = PyQuery(html)
    title = pg("title").text()

    async with pool.get() as conn:
        async with conn.cursor() as cur:
            sql = "insert into article(title) value('{}')".format(title)
            await cur.execute(sql)


async def consumer(pool):
    async with aiohttp.ClientSession() as session:
        while not stopping:
            if len(waiting_url) == 0:
                await asyncio.sleep(2)
                continue
            url = waiting_url.pop()

            if re.match("http://.*?jobbole.com/\d+/", url):
                if url not in seen_urls:
                    print("start scrape url: ", url)
                    asyncio.ensure_future(article_handler(url, session, pool))
                    # await asyncio.sleep(1)
            # else:
            #     if url not in seen_urls:
            #         asyncio.ensure_future(init_urls(url, session))


async def main(loop):
    pool = await aiomysql.create_pool(host='192.168.110.104', port=3306,
                                      user='root', password='mypassword',
                                      db='aiomysql_test', loop=loop,
                                      charset="utf8", autocommit=True)

    async with aiohttp.ClientSession() as session:
        html = await fetch(start_url, session)
        seen_urls.add(start_url)
        extract_url(html)

    asyncio.ensure_future(consumer(pool))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    task = asyncio.ensure_future(main(loop))
    loop.run_forever()

