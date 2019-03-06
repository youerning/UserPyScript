# -*- coding: utf-8 -*-
# @Author: youerning
# @Date:   2019-03-06 19:20:23
# @Last Modified by:   youerning
# @Last Modified time: 2019-03-06 22:17:30
import logging
import aiohttp
import asyncio
import json
import os
from random import randint
from random import choice
from datetime import datetime


ua_lst = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/537.36",
    "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US);",
    "Mozilla/5.0 (compatible; MSIE 10.0; Macintosh; Intel Mac OS X 10_7_3; Trident/6.0)'",
    "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0; GTB7.4; InfoPath.2; SV1; .NET CLR 3.3.69573; WOW64; en-US)",
    "Opera/9.80 (X11; Linux i686; U; ru) Presto/2.8.131 Version/11.11",
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2'",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/537.13 (KHTML, like Gecko) Chrome/24.0.1290.1 Safari/537.13",
    "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
    "Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1",
    "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    "Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25"
]

ua = choice(ua_lst)

headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6",
    "User-Agent": ua}

url_pattern = "https://www.91160.com/dep/getschmast/uid-139" +\
              "/depid-200080509/date-{date}/p-0.html"

file_cwd = os.path.dirname(os.path.abspath(__file__))
test_data_path = os.path.join(file_cwd, "test_data.json")
result_path = os.path.join(file_cwd, "result_data.json")
req_html_fp = os.path.join(file_cwd, "download.html")
now = datetime.now()
now_str = now.strftime("%Y-%m-%d")
url = url_pattern.format(date=now_str)
Enable_Test = False


def init_log():
    global logger
    logger = logging.getLogger("guahao")
    logger.setLevel(level=logging.DEBUG)
    handler = logging.FileHandler("guahao.log")
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


async def fetch(session, url):
    await asyncio.sleep(randint(3, 16))
    response = ""
    try:
        async with session.get(url) as resp:
            response = resp
            print("response status: ", resp.status)
            return await resp.json(content_type=None)
    except Exception as e:
        with open(req_html_fp, "w") as wf:
            wf.write(response.text())
        logger.error("request failed!!!")
        logger.error(e)
        logger.traceback()


def find_sch(data):
    """find schedule in data
    return {} for have no schedule
    otherwise, return data as follows
        [{
            "am": {
                "1": {
                    "schedule_id": 0,
                    "unit_id": "139",
                    "state": "1",
                    "doctor_id": "200139920",
                    "doctor_name": "\u8d75\u6ee1",
                    "to_date": "2019-03-07",
                    "yuyue_max": "7",
                    "yuyue_num": "7",
                    "youzhi_max": "0",
                    "youzhi_num": "0",
                    "origin_yuyue_max": "7",
                    "origin_yuyue_num": "7",
                    "origin_guahao_max": "0",
                    "origin_guahao_num": "0",
                    "left_num": "0",
                    "dep_id": "200080509",
                    "time_type": "am",
                    "time_type_desc": "\u4e0a\u5348",
                    "level_name": "\u4e3b\u6cbb\u533b\u5e08",
                    "level_code": "102524911",
                    "his_schedule_id": "1204_005998_2019-03-07_am",
                    "guahao_amt": "25",
                    "y_state": "0",
                    "y_state_desc": "\u5df2\u7ea6\u6ee1",
                    "schext_clinic_label": "",
                    "registration": "",
                    "self_paying": "",
                    "social_security": "",
                    "schextExtraAmt": "25",
                    "sch_detl_show": 1
                }
            }
        }]
    """
    order_lst = []
    if "sch" not in data:
        return order_lst

    data_sch = data["sch"]

    for doctor_id in data_sch:
        for am_or_pm in data_sch[doctor_id]:
            order_dict = data_sch[doctor_id][am_or_pm]
            available_order = find_order(order_dict)

            order_lst.extend(available_order)

    if os.path.exists(result_path):
        res_data = json.load(open(result_path))
    else:
        res_data = []

    ret = []
    for item in order_lst:
        if item not in res_data:
            ret.append(item)

    with open(result_path, "w") as wf:
        json.dump(ret, wf)

    return ret


def find_order(data):
    ret = []
    if isinstance(data, list):
        for order in data:
            # print("===> ", order)
            if order["y_state"] == "1":
                logger.info("===> found!!")
                ret.append(order)
    else:
        for sck_key in data:
            order = data[sck_key]
            # print("===> ", order)
            if order["y_state"] == "1":
                logger.info("===> found!!")
                ret.append(order)
    return ret


async def main():
    import sys
    print(sys.argv)
    while True:
        if len(sys.argv) > 1:
            Enable_Test = True
            logger.info("Just test")
            logger.debug("Try to request url: ")
            logger.debug(url)
            data = json.load(open(test_data_path))
            await asyncio.sleep(0.1)
        else:
            sleep_val = randint(3, 10)
            await asyncio.sleep(sleep_val)
            logger.info("sleep %s secs" % sleep_val)
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
                logger.debug("Try to request url: ")
                logger.debug(url)
                data = await fetch(session, url)

        data_sch = find_sch(data)

        if data_sch:
            logger.info("Found schedule: ")
            logger.info(json.dumps(data_sch))
        else:
            logger.info("have no schedule found")

        if Enable_Test:
            logger.info("run once for test mode")
            break


if __name__ == '__main__':
    init_log()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
