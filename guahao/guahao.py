# -*- coding: utf-8 -*-
# @Author: youerning
# @Date:   2019-03-06 19:20:23
# @Last Modified by:   youerning
# @Last Modified time: 2019-03-10 01:15:29
import logging
import time
import json
import os
import requests
from random import randint
from datetime import datetime


# ua_lst = [
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/537.36",
#     "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US);",
#     "Mozilla/5.0 (compatible; MSIE 10.0; Macintosh; Intel Mac OS X 10_7_3; Trident/6.0)'",
#     "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0; GTB7.4; InfoPath.2; SV1; .NET CLR 3.3.69573; WOW64; en-US)",
#     "Opera/9.80 (X11; Linux i686; U; ru) Presto/2.8.131 Version/11.11",
#     "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2'",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/537.13 (KHTML, like Gecko) Chrome/24.0.1290.1 Safari/537.13",
#     "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
#     "Mozilla/5.0 (Windows NT 6.2; Win64; x64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1",
#     "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1",
#     "Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25"
# ]

# # ua = choice(ua_lst)
# ua = ua_lst[0]


headers = {
    "Accept": "text/html,application/xhtml+xml," +
    "application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "www.91160.com",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/537.36"
}

url_yazhou = "https://www.91160.com/dep/getschmast/uid-139/" +\
             "depid-200080663/date-{date}/p-0.html"
url_yati = "https://www.91160.com/dep/getschmast/uid-139/" +\
           "depid-200080564/date-{date}/p-0.html"

file_cwd = os.path.dirname(os.path.abspath(__file__))
test_data_path = os.path.join(file_cwd, "test_data.json")
# cache data for don't repeat send main in 20 minus
cache_path = os.path.join(file_cwd, "cache.json")
now = datetime.now()
dt_format = "%Y-%m-%d %H:%M:%S"
now_str = now.strftime("%Y-%m-%d")


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


def fetch(url):
    # await asyncio.sleep(randint(3, 16))
    try:
        resp = requests.get(url, headers=headers)
        if resp.ok:
            logger.info("request successfully")
            resp_json = resp.json()
            # from pprint import pprint
            # pprint(resp_json)
            return resp_json
        else:
            logger.info("request failed")
            return {}

    except Exception as e:
        logger.error("request failed!!!")
        logger.error(e)
        logger.exception("Traceback: ")
        return {}


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

    ret = []
    for item in order_lst:
        ret.append(item)

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


def send_mail(data):
    # print(len(data))
    import smtplib
    from email.header import Header
    from email.mime.text import MIMEText
    from email.utils import parseaddr
    from email.utils import formataddr

    send_data = []
    if os.path.exists(cache_path):
        cache_data = json.load(open(cache_path))
    else:
        cache_data = {}

    for item in data:
        item_str = json.dumps(item)
        if item_str in cache_data:
            last_found = cache_data[item_str]
            last_found_date = datetime.strptime(last_found, dt_format)
            diff = now - last_found_date
            if diff.total_seconds() > 1200:
                send_data.append(item)
        else:
            send_data.append(item)

    if send_data:
        cache_data = {}
        for send_data_item in send_data:
            send_data_item_str = json.dumps(item)
            cache_data[send_data_item_str] = now.strftime(dt_format)

        with open(cache_path, "w") as wf:
            json.dump(cache_data, wf)

        def format_addr(s):
            name, addr = parseaddr(s)
            return formataddr((Header(name, "utf-8").encode(), addr))

        from_email = "woshiy0uer123@163.com"
        from_email_pwd = "1234qwerasdf"
        to_email = ["673125641@qq.com", "75023492@qq.com"]
        smtp_server = "smtp.163.com"
        msg = "<html><body><h2>发现以下可预约信息</h2>"
        for send_data_item in send_data:
            msg += "<p> 科室: %s</p>" % send_data_item["keshi"]
            msg += "<p> 医生: %s</p>" % send_data_item["doctor_name"]
            msg += "<p> 详细日期: %s/%s</p>" % (send_data_item["to_date"], send_data_item["time_type_desc"])
            msg += "<br><br>"
        msg += "</body></html>"

        # print(msg)
        msg = MIMEText(msg, "html", "utf-8")
        msg["From"] = format_addr(from_email)
        msg["To"] = ";".join(to_email)
        msg["Subject"] = Header("挂号监控", "utf-8").encode()

        server = smtplib.SMTP(smtp_server, 25)
        server.set_debuglevel(1)
        server.login(from_email, from_email_pwd)
        server.sendmail(from_email, to_email, msg.as_string())


def main():
    import sys
    sleep_sec = randint(3, 10)
    logger.info("sleep %s secs " % sleep_sec)
    time.sleep(sleep_sec)
    url_lis = [url_yazhou, url_yati]
    url_lis = [url.format(date=now_str) for url in url_lis]

    send_data = []
    for index, url in enumerate(url_lis):
        if len(sys.argv) > 1:
            logger.info("Just test")
            logger.debug("Try to request url: ")
            logger.debug(url)
            data = json.load(open(test_data_path))
        else:
            logger.debug("Try to request url: ")
            logger.debug(url)
            data = fetch(url)

        if data:
            keshi = ""
            if index == 0:
                keshi = "牙周病科"
            else:
                keshi = "牙体牙髓病科"

            data_sch = find_sch(data)
            for data_sch_item in data_sch:
                data_sch_item["keshi"] = keshi
                send_data.append(data_sch_item)

            if data_sch:
                logger.info("Found schedule: ")
                logger.info("json format: \n%s" % json.dumps(data_sch, indent=4))
                logger.info("Valuable data:")
                for item in data_sch:
                    logger.info("doctor_name: %s" % item["doctor_name"])
                    logger.info("date desc: %s/%s" % (item["to_date"], item["time_type_desc"]))
            else:
                logger.info("have no schedule found")
    if send_data:
        send_mail(send_data)


if __name__ == '__main__':
    init_log()
    main()
