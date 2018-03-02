#coding: utf-8
"""
monitor change of stock price every period that user set
requirement 1: add specify stock in a way, confile file or web page
requirement 2: add rule of monitor, price change today, price change recent day
requirement 3: inform specify user immediately with specify way of notice, like email,etc.
"""
import pandas as pd
import tushare as ts
import datetime
import os
import json
from configparser import ConfigParser

from utils import cache

confile = "monitor.conf"
name_cache = "stock.json"
sent_cache = "sent.json"

conf = ConfigParser()
conf.read(confile)


class bar(object):
    """a custom data type
    """

    def __init__(self, code, code_data):
        self.code = code
        self._df = code_data
        self.data = dict(code_data.iloc[-1])
        self.get_stockname()

    def get_stockname(self):
        if not os.path.exists(name_cache):
            down_code()
        stocks = json.load(open(name_cache))
        stock_name = stocks.get(self.code, "None")
        self.name = stock_name


def down_code():
    """download code and name of all of A stock and save as stock.json in working directory

    Returns:
        None
    """
    import requests
    import re
    from bs4 import BeautifulSoup
    import json
    url = "http://quote.eastmoney.com/stocklist.html"
    headers = {"user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"}
    page = requests.get(url, headers=headers)

    soup = BeautifulSoup(page.content.decode("gbk"), "lxml")
    pattern = "(.+?)\((\d+)\)"
    css_select = "div#quotesearch ul li a"

    stock_lis = soup.select(css_select)
    stocks = {}
    for stock in stock_lis:
        ret = re.findall(pattern, stock.text)
        stocks[ret[0][1]] = ret[0][0]

    with open(name_cache, "w") as wf:
        json.dump(stocks, wf)


def trade_time():
    """is ts trade time

    Returns:
        True or False
    """
    now = datetime.datetime.now()
    # the trade period of morning
    mopen = "9:30"
    mend = "11:30"

    # the trade period of afternoon
    aopen = "13:00"
    aend = "15:00"

    mopen = gen_time(mopen)
    mend = gen_time(mend)
    aopen = gen_time(aopen)
    aend = gen_time(aend)

    # whether now in morning period
    morning = mopen < now < mend
    # whether now in afternoon period
    afternoon = aopen < now < aend
    if morning or afternoon:
        return True
    else:
        return False


def gen_time(dt):
    """generate the time for specify hour and minute,like t=9:30

    Args:
        dt: the specify time in format, 9:30

    Returns:
        return the datetime with specify hour and minute today
        example:

        datetime.datetime(2018, 3, 1, 9, 30)
    """
    moment = datetime.datetime.strptime(dt, "%H:%M")
    ret = datetime.datetime.combine(datetime.datetime.today(), moment.time())

    return ret


@cache
def fetch(code):
    """fetch history data of the code of stock
    fetch the data of stock in recent year,may be 3 year, use the method get_k_data of tushare

    Args:
        code: the code of specify stock

    Returns:
        a dataframe object of pandas
        example:

             open  close   high    low      volume    code
        date
        2015-07-14  4.333  4.333  4.333  4.333   2443864.0  000725
        2015-07-15  4.677  3.958  4.677  3.939  20725290.0  000725
        2015-07-16  3.939  4.027  4.136  3.762  12367056.0  000725
        2015-07-17  4.047  4.254  4.333  4.037  14418724.0  000725
        2015-07-20  4.264  4.234  4.342  4.165  13036186.0  000725
    """
    df = ts.get_k_data(code)
    df.index = pd.to_datetime(df.date)
    df.drop("date", axis=1, inplace=True)
    return df


def pchange(df):
    """add two column of price-change to the df the args pass
    add the column name pchange mean price change ration.
    add the column name change mean how many tick changed.

    Args:
        df: a dataframe of specify stock.

    Returns:
        a dataframe object of pandas
        example:

             open  close   high    low      volume    code   pchange  change
        date
        2015-07-14  4.333  4.333  4.333  4.333   2443864.0  000725       NaN     NaN
        2015-07-15  4.677  3.958  4.677  3.939  20725290.0  000725 -0.086545  -0.375
        2015-07-16  3.939  4.027  4.136  3.762  12367056.0  000725  0.017433   0.069
        2015-07-17  4.047  4.254  4.333  4.037  14418724.0  000725  0.056370   0.227
        2015-07-20  4.264  4.234  4.342  4.165  13036186.0  000725 -0.004701  -0.020
    """
    df["pchange"] = df.close.pct_change()
    df["change"] = df.close.diff()

    return df


def ma(df, days=[10, 20, 50]):
    """add ma to the df
    add ma10,20,50 to the dataframe the args pass

    Args:
        df: a dataframe of specify stock.

    Returns:
        a dataframe object of pandas
        example:

            open  close  high   low      volume    code   pchange  change  \
        date
        2018-02-22  5.59   5.66  5.68  5.54   5418361.0  000725  0.023508    0.13
        2018-02-23  5.64   5.58  5.66  5.51   5013632.0  000725 -0.014134   -0.08
        2018-02-26  5.65   5.79  5.86  5.47  11591063.0  000725  0.037634    0.21
        2018-02-27  5.80   5.71  5.85  5.68   6707226.0  000725 -0.013817   -0.08
        2018-02-28  5.61   5.65  5.73  5.56   4516456.0  000725 -0.010508   -0.06

                     MA10    MA20    MA50
        date
        2018-02-22  5.502  5.8915  5.8682
        2018-02-23  5.492  5.8380  5.8682
        2018-02-26  5.499  5.7950  5.8706
        2018-02-27  5.534  5.7560  5.8688
        2018-02-28  5.559  5.7110  5.8672
    """

    for ma in days:
        column_name = "MA{}".format(ma)
        df[column_name] = pd.rolling_mean(df.close, ma)

    return df


def report(s_lis, h_lis, subject="Breakthrough"):
    """create report for given code

    Args:
        sbrk: soft-breakthrough list
        hbrk: hard-breakthrough list
        subject: subject of notification

    Returns:
        a string of report
        example:

        breakthrough: soft-breakthrough
        Code: 000725 京东方A
        Price:5.82 3.2%(Percent change) 0.23(Price change)
        MA10/20/50:5.72 5.68 5.56
    """
    ret = []
    if subject == "Breakthrough":
        tpl = """breakthrough: {brk}
        Code: {code} {name}
        Price: {close} {pchange:.3} {change:.3}
        MA10/20/50: {MA10:.5} {MA20:.5} {MA50:.5}
        """
        for stock in s_lis:
            # print(code.name)
            if should_sent(stock.code, "soft-breakthrough"):
                msg = tpl.format(name=stock.name, brk="soft-breakthrough(3%)", **stock.data)
                ret.append(msg)

        for stock in h_lis:
            # print(code.name)
            if should_sent(stock.code, "hard-breakthrough"):
                msg = tpl.format(name=stock.name, brk="hard-breakthrough(5%)", **stock.data)
                ret.append(msg)

    elif subject == "Withdraw":
        tpl = """withdraw: {wd}
        Code: {code} {name}
        Price: {close} {pchange:.3} {change:.3}
        MA10/20/50: {MA10:.5} {MA20:.5} {MA50:.5}
        """

        for stock in s_lis:
            # print(code.name)
            if should_sent(stock.code, "soft-withdown"):
                msg = tpl.format(name=stock.name, wd="soft-withdown(3%)", **stock.data)
                ret.append(msg)

        for stock in h_lis:
            # print(code.name)
            if should_sent(stock.code, "hard-withdown"):
                msg = tpl.format(name=stock.name, wd="hard-withdown(5%)", **stock.data)
                ret.append(msg)

    if ret:
        split_line = "".join(["\n", "-" * 30, "\n"])
        message = split_line.join(ret)
        inform(subject, message)


def inform(subject, msg):
    """inform user
    """
    # from utils import sendMail
    # print("send eamil...")
    # sendMail(subject, msg)
    print(subject, "\n", msg)


def should_sent(code, status):
    """have it sent?
    if the stock have sent at same price change point before,just ingore.

    Args:
        code: code of the stock
        status: status of the stock, contain soft-withdraw,soft-breakthrough,etc.

    Returns:
        True or False
        example:

        if it never sent before,send.
        if it have sent with soft-breakthrough and soft-breakthrough now, ingore this.
        if it have sent with soft-breakthrough and hard-breakthrough now, sned.
        if it have sent with hard-breakthrough and soft-breakthrough now, ingore.
        if it have sent with hard-breakthrough and hard-breakthrough now, ingore.
    """
    tformat = "%Y-%m-%d %H:%M"
    now = datetime.datetime.now()
    if not os.path.exists(sent_cache):
        # print("not exists")
        with open(sent_cache, "w") as wf:
            content = {}
            content["last_time"] = now.strftime(tformat)
            content["status"] = {}
            json.dump(content, wf)

    content = json.load(open(sent_cache, "r"))
    last_time = datetime.datetime.strptime(content["last_time"], tformat)

    if now.date() > last_time.date():
        print("before")
        content["last_time"] = now.strftime(tformat)
        content["status"] = {}
        content["status"][code] = status
        with open(sent_cache, "w") as wf:
            json.dump(content, wf)
        return True

    elif now.date() == last_time.date():
        print("now")
        last_status = content["status"].get(code)
        if last_status == status:
            return False
        else:
            content["status"][code] = status
            with open(sent_cache, "w") as wf:
                json.dump(content, wf)
                return True
    else:
        print("strange date...")
        return False


def main():
    # define hard-breakthrough,soft-breakthrough list
    hbrk = []
    sbrk = []

    # define hard-withdraw, sort-withdraw list
    hwd = []
    swd = []

    attention_lis = conf["default"]["attention"]
    attention_lis = attention_lis.split()

    position_lis = conf["default"]["position"]
    position_lis = position_lis.split()

    # breakthrough, index 0 is soft-breakthrough, index 1 is hard-breakthrough
    brk = conf["default"]["breakthrough"]
    brk = [float(p) for p in brk.split()]

    # withdraw, index 0 is soft,index 1 is hard
    wd = conf["default"]["withdraw"]
    wd = [float(p) for p in wd.split()]

    for stock in attention_lis:
        df = fetch(stock)
        df = pchange(df)
        df = ma(df)

        if df.pchange[-1] > brk[1]:
            # print(stock)
            data = bar(stock, df)
            hbrk.append(data)
            continue
        if df.pchange[-1] > brk[0]:
            # print(stock)
            data = bar(stock, df)
            sbrk.append(data)

    if hbrk or sbrk:
        report(sbrk, hbrk)

    for stock in position_lis:
        df = fetch(stock)
        df = pchange(df)
        df = ma(df)

        if df.pchange[-1] < -wd[1]:
            data = bar(stock, df)
            hwd.append(data)
            continue
        if df.pchange[-1] < -wd[0]:
            data = bar(stock, df)
            swd.append(data)

    if swd or hwd:
        report(swd, hwd, subject="Withdraw")


if __name__ == '__main__':
    if trade_time:
        main()
