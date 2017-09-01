#coding: utf-8
from __future__ import print_function
import logging
import sys
from ConfigParser import ConfigParser
import requests
import csv
import os
import argparse
from os import path
from glob import glob
from datetime import datetime
import json
import sys
reload(sys)

sys.setdefaultencoding('utf-8')


def InitLog(filename, console=True):
    logger = logging.getLogger(filename)
    logger.setLevel(logging.DEBUG)

    logpath = filename + ".log"
    fh = logging.FileHandler(logpath)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] -%(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if console:
        logger.addHandler(ch)

    return logger


# 20*1 + 12*7 + 15*2 + 10*1 columnss
headerTemplate = """|{ph:-<154}|
|{company:<154}|
|{ph:->154}|
|server              |flavor      |flavor-price|datadisk    |disk-price  |days        |start-time  |end-time    |server-billing |disk-billing   |sum       |\n|""" + "-" * 154 + "|\n"

rowTemplate = """|{:<20}|{:<12}|{:<12.2f}|{:<12.2f}|{:<12.2f}|{:<12}|{:%Y-%m-%d  }|{:%Y-%m-%d  }|{:<15.2f}|{:<15.2f}|{:<10.2f}|\n"""
sumTemplate = """|{:-<154}|
|{:<20}|{:<90}|{:<15}|{:<15}|{:<10}|\n"""
footerTemplate = "-" * 136

csvHeaderTpl="server,flavor,flavor-price,datadisk,disk-price,days,start-time,end-time,server-billing,disk-billing,sum"

def headerGen(company, tpl=headerTemplate):
    # generate the header of stdout
    c = company
    ret = tpl.format(ph="", company=c)

    return ret


def rowGen(lis, tpl=rowTemplate):
    # generate the row of each server
    ret = tpl.format(*lis)

    return ret


def sumGen(lis, tpl=sumTemplate):
    # generate the row of sum
    lis.insert(0, "")
    lis.insert(1, "Sum")
    lis.insert(2, "")
    ret = tpl.format(*lis)

    return ret


def checkConf(logfile, confile, local=False):
    """read the config file for check"""

    if not os.path.exists(confile):
        logfile.critical("please specify the conf file path")
        return False

    cf = ConfigParser()
    cf.read(confile)
    try:
        sec = cf.sections()
    except Exception as e:
        logfile.critical(e)
        sys.exit(1)

    secLis = ['openstack', 'price']
    openLis = ["auth_url", "uname", "passwd", "tenant"]
    priceList = ["disk", "1-2", "2-2", "2-4", "4-4", "4-8", "8-16", "16-32"]

    testsec = [s for s in secLis if s in sec]
    if len(testsec) < 2 and not local:
        logfile.critical("[openstack] or [price] not in confile")
        sys.exit(1)

    if not local:
        for i in openLis:
            if i not in cf.options("openstack"):
                logfile.critical("some auth info not in [openstack] section ")
                sys.exit(1)

    for i in priceList:
        if i not in cf.options("price"):
            logfile.critical("some price info not in [price] section")
            print("some price info not in [price] section")
            sys.exit(1)

    logfile.info("confile test succuessful!!!")
    return True


class base(object):
    """init the info of all compute, and get the token for access the api"""
    def __init__(self, confile, logfile):
        headers = {}
        headers["Content-Type"] = "application/json"

        self.cf = ConfigParser()
        self.cf.read(confile)
        self.conf = {k: v for k, v in self.cf.items("openstack")}
        self.headers = headers

        self.logfile = logfile
        self.catalog, self.token = self.getToken()

    def getURL(self, catalog, name):
        """
        get the public url of openstack services
        """
        url = [url for url in self.catalog if url["name"] == name]
        if url:
            url = url[0]["endpoints"][0]["publicURL"]

        return url

    def getToken(self):
        headers = self.headers
        url = self.conf["auth_url"] + "/tokens"
        data = '{"auth": {"tenantName": "%s", \
                 "passwordCredentials": {"username": "%s", "password": "%s"}}}'
        data = data % (self.conf["tenant"],
                       self.conf["uname"], self.conf["passwd"])

        try:
            msg = "Acquire token from %s " % self.conf["auth_url"]
            self.logfile.debug(msg)
            ret = requests.post(url, data=data, headers=headers)
            ret = ret.json()
        except Exception as e:
            msg = "Acuire Token failed \ndata: %s\n headers: %s" % (data, headers)
            self.logfile.critical(msg)
            self.logfile.critical(e)

        catalog = ret["access"]["serviceCatalog"]
        token = ret["access"]["token"]["id"]

        return catalog, token

    def getResp(self, suffix, method, data=None,
                headers=None, params=None, isjson=True, api="nova"):
        """return the result of requests"""
        apiURL = self.getURL(self.catalog, api)
        url = apiURL + suffix
        if headers is None:
            headers = self.headers.copy()
        headers["X-Auth-Token"] = self.token

        req = getattr(requests, method)
        try:
            ret = req(url, data=data,
                      headers=headers, params=params, verify=False)
            #print(ret.url)
            #print(ret.content)

            self.logfile.debug("request url:%s" % ret.url)
            if ret.status_code == 401:
                self.logfile.warning("Token expired, acquire token again")
                self.catalog, self.token = self.getToken()
                headers["X-Auth-Token"] = self.token
                self.logfile.debug("Request headers:%s" % ret.request.headers)
                ret = req(url, data=data, headers=headers)

            if isjson:
                retCode = ret.status_code
                if ret.content:
                    ret = ret.json()
                else:
                    ret = {}

                ret["status_code"] = retCode

        except Exception as e:
            msg = "The method:%s for path:%s failed \ndata:%s \nheaders:%s" % (method, suffix, data, headers)
            self.logfile.critical(msg)
            self.logfile.critical(e)
            sys.exit(1)
            ret = None

        return ret


class billing(base):
    """the openstack rest api client """
    def __init__(self, confile, logfile, local=False):
        if not local:
            super(billing, self).__init__(confile, logfile)
            self.conf = {k: v for k, v in self.cf.items("price")}
        else:
            self.logfile = logfile
            self.cf = ConfigParser()
            self.cf.read(confile)
            self.conf = {k: v for k, v in self.cf.items("price")}
        self.dataSet = {}

    def getInstances(self):
        # get instances detail
        suffix = "/servers/detail"
        resp = self.getResp(suffix, "get")

        return resp

    def apiRead(self, project, start=None):
        # get the usage
        suffix = "/os-simple-tenant-usage/%s" % project

        resp = self.getResp(suffix, "get")

        return resp

    def getProjects(self):
        # get the project list
        suffix = "/v2.0/tenants"

        resp = self.getResp(suffix, "get", api="keystone")

        return resp

    def calcCSV(self, csvPath="."):
        # calc with csv files

        csvPath = path.join(csvPath, "*csv")
        csvs = glob(csvPath)
        self.logfile.info("find local file: %s" % csvs)

        for csvFile in csvs:
            company = path.basename(csvFile).split("-")[0]
            serverLis = self.csvRead(csvFile)
            self.dataSet[company] = serverLis

    def calcAPI(self):
        # calc with api
        # store records in sqlite3 db
        pass

    def csvRead(self, csvFile):
        # usage
        csvFile = open(csvFile)
        csvReader = csv.reader(csvFile)
        csvRet = [line for line in csvReader]
        serverLis = csvRet[9:]
        # system disk now
        retLis = []
        for server in serverLis:
            now = datetime.now()
            flavor = "{}-{}".format(server[1], int(server[2]) / 1024)
            flavorPrice = float(self.conf[flavor])
            strformat = "%b. %d, %Y"
            dataDisk = int(server[-1])
            dataDiskPrice = float(self.conf["disk"])
            createDate = server[5].strip()
            createTime = datetime.strptime(createDate, strformat)
            diff = now - createTime
            days = diff.days + 1
            # print(flavor, flavorPrice, dataDisk, dataDiskPrice)
            serverSum = days * flavorPrice
            dataDiskSum = dataDisk * days * dataDiskPrice
            total = serverSum + dataDiskSum
            retLis.append([server[0], flavor, flavorPrice, dataDisk,
                        dataDiskPrice, days, createTime, now, serverSum,
                        dataDiskSum, total])

        totalS = sum([x[8] for x in retLis])
        totalD = sum([x[9] for x in retLis])
        totalAll = totalS + totalD
        retLis.append([totalS, totalD, totalAll])

        return retLis

    def stdout(self):
        # stdout
        companyLis = self.dataSet.keys()
        retLis = []
        for company in companyLis:
            ret = self.stdRender(company, self.dataSet[company])
            ret = "".join(ret)
            retLis.append(ret)

        output = "\n".join(retLis)
        print(output)

    def stdRender(self, company, data):
        # render to stdout
        lis = []
        header = headerGen(company)
        lis.append(header)

        for row in data[:-1]:
            r = rowGen(row)
            lis.append(r)

        r = sumGen(data[-1])
        lis.append(r)

        return lis

    def jsonout(self):
        # json out
        print(json.dumps(self.dataSet, indent=True, default=str))

    def csvout(self):
        # csv out
        companyLis = self.dataSet.keys()
        csvHeader = csvHeaderTpl.split(",")
        csvHeader = [x.strip() for x in csvHeader]

        for company in companyLis:
            with open(company + ".csv", "w") as wf:
                rows = self.dataSet[company]
                csvWriter = csv.writer(wf)
                csvWriter.writerow(csvHeader)
                csvWriter.writerows(rows[:-1])
                lastRow = rows[-1]
                rowFooter = "," * 10
                rowFooter = rowFooter.split(",")
                rowFooter[0] = "Summary"
                rowFooter[-3:len(rowFooter) + 1] = lastRow[-3:len(lastRow) + 1]
                csvWriter.writerow(rowFooter)

    def billing(self, output="std"):
        # the billing export
        export = getattr(self, output + "out", None)

        if not export:
            self.logfile.critical("output method %s don't exist!!!")
            sys.exit(1)

        try:
            export()
        except Exception as e:
            self.logfile.critical(e)
            self.logfile.critical("export faild")
        finally:
            self.logfile.info("~done~")


def calc(logfile, confile,
         local=False, csvPath=".", output="stdout"):
    # main function
    bill = billing(confile, logfile, local=local)

    if local:
        bill.calcCSV(csvPath=csvPath)
    else:
        bill.calcAPI()

    logfile.info("calculate completely")
    bill.billing(output=output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("conf")
    parser.add_argument("-d", "--debug", help="debug on or off",
                        action="store_true")
    parser.add_argument("-t", "--test", help="check the conf file",
                        action="store_true")
    parser.add_argument("-p", "--path", help="the local csv dir")
    parser.add_argument("-o", "--output", help="output format: csv, stdout, json\
                                        default stdout")
    args = parser.parse_args()
    confile = args.conf
    billlog = InitLog("billing", console=args.debug)
    output = "std"

    if args.output:
        output = args.output

    if args.path:
        if checkConf(billlog, confile, local=True):
            calc(billlog, confile, local=True,
                 csvPath=args.path, output=output)
    elif args.test:
        checkConf(billlog, confile)
    else:
        if checkConf(billlog, confile):
            calc(confile, billlog, output=output)
        else:
            billlog.critical("configuration incorrect!!!")
