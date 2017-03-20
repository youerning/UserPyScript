#coding: utf-8
import sys
import requests
import time
import logging
import os
import subprocess as sp
from ConfigParser import ConfigParser
from pprint import pprint
import datetime
import json


confFile="/etc/unit.conf"
logfile = "/var/log/selfm.log"
debug=False

level = logging.WARNING if not debug else logging.DEBUG
logging.basicConfig(level=level,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename=logfile,
                filemode='a')

def tons(dateStr):
    """convert the isodateformate str to unix timestamp"""
    try:
        d = datetime.datetime.strptime(dateStr,'%Y-%m-%dT%H:%M:%S.%f')
    except Exception as e:
        d = datetime.datetime.strptime(dateStr,'%Y-%m-%dT%H:%M:%S')

    d = d + datetime.timedelta(hours=8)
    ret = d.strftime("%s000")

    return int(ret)

class baseInfo(object):
    """init the info of API, and get the token for access the api"""

    def __init__(self, token=None):

        headers = {}
        headers["Content-Type"] = "application/json"
        self.headers = headers

        self.cf = ConfigParser()
        self.cf.read(confFile)
        self.conf = self.getConf()

        self.catalog, self.token = self.getToken()
        self.url = [url for url in self.catalog if url["name"] == "ceilometer"]
        self.url = self.url[0]["endpoints"][0]["publicURL"]

    def getConf(self):
        try:
            conf = {
                "url": self.cf.get("ser","OS_AUTH_URL"),
                "uname" : self.cf.get("ser","OS_USERNAME"),
                "passwd" : self.cf.get("ser","OS_PASSWORD"),
                "tname" : self.cf.get("ser","OS_TENANT_NAME")}

        except Exception as e:
                logging.critical("加载配置文件失败")
                logging.critical(e)

        return conf

    def getToken(self):
        headers = self.headers
        url = self.conf["url"] + "/tokens"
        data = '{"auth": {"tenantName": "%s", "passwordCredentials": {"username": "%s", "password": "%s"}}}'
        data = data % (self.conf["tname"], self.conf["uname"], self.conf["passwd"])
        try:
            logging.debug("开始获取Token")
            ret = requests.post(url, data=data, headers=headers)
            #print ret.url
            logging.debug("request url:%s" % ret.url)
            ret = ret.json()
        except Exception as e:
            msg = "获取Token失败 data:%s headers:%s" % (data, headers)
            logging.critical(msg)
            logging.critical(e)

        catalog = ret["access"]["serviceCatalog"]
        token = ret["access"]["token"]["id"]

        return catalog, token

    def getCResp(self, suffix, method, data=None, headers=None, params=None, isjson=True):
        """return the result of ceilometer response"""
        url = self.url + suffix
        if headers == None:
            headers = self.headers.copy()
        headers["X-Auth-Token"] = self.token

        req = getattr(requests, method)
        try:
            ret = req(url, data=data, headers=headers, params=params, verify=False)
            #print ret.url
            logging.debug("request url:%s" % ret.url)
        except Exception as e:
            msg = "%s访问%s失败 data:%s headers:%s" % (method, suffix, data, headers)
            logging.critical(msg)
            logging.critical(e)
            sys.exit(1)

        if ret.status_code == 401:
            self.catalog, self.token = self.getToken()
            headers["X-Auth-Token"] = self.token
            ret = req(url, data=data, headers=headers)

        if isjson:
            ret = ret.json()

        return ret

class ceil(baseInfo):
    """the class for grab ceilometer metric"""
    def __init__(self, vm, timeRange):
        super(ceil, self).__init__()
        self.timeRange = timeRange
        self.vm = vm
        self.qge = "&q.field=timestamp&q.op=lt&q.value=%s" % self.timeRange[0]
        self.qlt = "&q.field=timestamp&q.op=ge&q.value=%s" % self.timeRange[1]
        self.qr = "?q.field=resource_id&q.op=eq&q.value=%s" % self.vm

    def getData(self, suffix, plotype, title):
        data = []
        options = {}

        for s in suffix:
            s2 = "".join([s, self.qr, self.qge, self.qlt, '&limit=10000'])

            #print s2
            resp = self.getCResp(s2, "get")
            if resp:
                if s in ["/v2/meters/disk.read.bytes.rate", "/v2/meters/disk.write.bytes.rate"]:
                    volumes = [[tons(i["recorded_at"]), i["counter_volume"] / 1024  ] for i in resp ]
                    unit = "KB/s"
                    name = s.split("/")[-1]
                else:
                    volumes = [[tons(i["recorded_at"]), i["counter_volume"]] for i in resp ]
                    unit = resp[1]["counter_unit"]
                    name = s.split("/")[-1]
                    

                seq = {"type": plotype,
                       "name": name,
                       "data": volumes}
            
                data.append(seq)
            else:
                unit = "None"
                title = "No Data"

            options["unit"] = unit
            options["title"] = title
            ret = [options, data]
                
        return ret

    def cpu(self, plotype="line", title="cpu_util"):
        """return the data series of highchart need 
        ret = [options, data]
            options["unit"] = "None"
            options["title"] = "No Data"
            data = [{type:plottype,name:name,data:[nstime, datapoint]}]
        """

        suffix = ["/v2/meters/cpu_util"]
        ret = self.getData(suffix, plotype, title)

        return ret

    def disk(self, plotype="line", title="diskio"):
        suffix = ["/v2/meters/disk.read.bytes.rate", "/v2/meters/disk.write.bytes.rate"]
        ret = self.getData(suffix, plotype, title)
        return ret

    def mem(self, plotype="line", title="memory_usage"):
        suffix = ["/v2/meters/memory.resident"]
        #suffix = ["/v2/meters/memory.resident", "/v2/meters/memory"]
        ret = self.getData(suffix, plotype, title)
        
        return ret

    def net(self, plotype="line"):
        suffix = "/v2/query/samples"
        meters = ["network.incoming.bytes.rate", "network.outgoing.bytes.rate"]
        options = {}
        data = []
        kb = 1024
        mb = 1024 * 1024
        
        for m in meters:
            d = {
                "filter": "{\"and\": [{\"=\": {\"counter_name\": \"%s\"}}, {\"=~\": {\"resource_id\":\".*%s.*\"}}, {\"<\": {\"timestamp\": \"%s\"}}, {\">\": {\"timestamp\": \"%s\"}}]}" % (m, self.vm, self.timeRange[0], self.timeRange[1])
                }
            #print d
            resp = self.getCResp(suffix, "post", data=json.dumps(d))
            if resp:
                volumes = [[tons(i["recorded_at"]), i["volume"] / 1024 ] for i in resp ]
                unit = "KB/s"
                name = m
                
                seq = {"type": plotype,
                       "name": name[8:16],
                       "data": volumes}
            
                data.append(seq)
            else:
                unit = "None"
                title = "No Data"

        options["unit"] = unit
        options["title"] = "netio"
        ret = [options, data]
        return ret

def test():
    now = datetime.datetime.utcnow()
    yesterday = now + datetime.timedelta(hours=-2)
    now = now.isoformat()
    print now
    yesterday = yesterday.isoformat()
    c = ceil("8fc2a76e-90c5-491e-b207-28e90d5a5fab", (now, yesterday))
    pprint(c.net())
    #pprint(c.net())
    
if __name__ == "__main__":
    test()

