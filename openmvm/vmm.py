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
import shutil
from urllib import quote
"""
step1,获取数据
  通过ceilometer /v2/query/samples接口获取监控信息
  除network之外每个指标一次性取所有实例的数据

step2,判断数据
 阈值:
   cpu => 80%
   diskio => 1048576
   mem => 80%
   netio => 1048576

 结果三种情形
 一:
    全部OK
 二:
    部分OK
 三:
    全部超出阈值

step3,发送结果
   cmd_mod=2&cmd_typ=30&host=CVM&service=%s&plugin_state=%s&plugin_output=%s" % (service, state, output)
"""

#confFile="/etc/unit.conf"
confFile="unit.conf"
logfile = "/tmp/openmvm.log"
debug=True


TD = {
    "warnning": {
    "cpu" : 0.8,
    "diskio" : 1048576,
    "mem" : 0.8,
    "netio" : 1048576

},
    "critical": {
    "cpu" : 0.9,
    "diskio" : 2097152,
    "mem" : 0.9,
    "netio" :2097152
    }
}

checkList = ["cpu", "mem", "diskio", "netio"]

def InitLog(filename, console=False, logpath="/var/log/vmm/"):
    logger = logging.getLogger(filename)
    logger.setLevel(logging.DEBUG)

    logpath = logpath + filename + ".log"
    fh = logging.FileHandler(logpath)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    logger.addHandler(fh)
    if console:
        logger.addHandler(ch)

    return logger

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
        self.Curl = [url for url in self.catalog if url["name"] == "ceilometer"]
        self.Nurl = [url for url in self.catalog if url["name"] == "nova"]
        self.Curl = self.Curl[0]["endpoints"][0]["publicURL"]
        self.Nurl = self.Nurl[0]["endpoints"][0]["publicURL"]

    @staticmethod
    def checkconf():
        pass

    def getConf(self):
        conf = None
        try:
            conf = {
                "url": self.cf.get("ser","OS_AUTH_URL"),
                "uname" : self.cf.get("ser","OS_USERNAME"),
                "passwd" : self.cf.get("ser","OS_PASSWORD"),
                "tname" : self.cf.get("ser","OS_TENANT_NAME"),
                "nagiosURL" : self.cf.get("ser","nagiosurl"),
                    }

        except Exception as e:
                logging.critical("配置文件配置有误")
                logging.critical(e)
                sys.exit(1)

        return conf

    def getToken(self):
        headers = self.headers
        url = self.conf["url"] + "/tokens"
        data = '{"auth": {"tenantName": "%s", "passwordCredentials": {"username": "%s", "password": "%s"}}}'
        data = data % (self.conf["tname"], self.conf["uname"], self.conf["passwd"])
        try:
            logging.debug("开始获取Token")
            ret = requests.post(url, data=data, headers=headers, verify=False)
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
        url = self.Curl + suffix
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

    def getNResp(self, suffix, method, data=None, headers=None, params=None, isjson=True):
        """return the result of ceilometer response"""
        url = self.Nurl + suffix
        if headers == None:
            headers = self.headers.copy()
        headers["X-Auth-Token"] = self.token

        req = getattr(requests, method)
        try:
            ret = req(url, data=data, headers=headers, params=params, verify=False)
            #print ret.url
            #print ret.content
            logging.debug("request url:%s" % ret.url)
        except Exception as e:
            msg = "%s访问%s失败 data:%s headers:%s" % (method, suffix, data, headers)
            logging.critical(msg)
            logging.critical(e)
            sys.exit(1)

        if ret.status_code == 401:
            self.catalog, self.token = self.getToken()
            headers["X-Auth-Token"] = self.token
            ret = req(url, data=data, headers=headers, verify=False)

        if isjson:
            ret = ret.json()

        return ret

    def getID(self):
        """
        get all node id
        """
        suffix = "/servers/detail?all_tenants=1"
        url = self.Nurl
        resp = self.getNResp(suffix, "get")
        #print resp

        node = {node["id"]:node["name"] for node in resp["servers"] if node["status"] == "ACTIVE"}

        return node

class ceil(baseInfo):
    """the class for grab ceilometer metric"""
    def __init__(self, vm):
        super(ceil, self).__init__()
        self.vm = vm
        #self.qr = "?q.field=resource_id&q.op=eq&q.value=%s" % self.vm

    def getDatav1(self, suffix):
        """
        compatible with the ceilometer v1 rest api
        """
        ret = list()

        for s in suffix:
            s2 = "".join([s, self.qr, '&limit=1'])

            #print s2
            resp = self.getCResp(s2, "get")
            #print resp
            if resp:
                if s in ["/v2/meters/disk.read.bytes.rate", "/v2/meters/disk.write.bytes.rate"]:
                    volumes = resp[0]["counter_volume"] / 1024
                else:
                    volumes = resp[0]["counter_volume"]
            else:
                volumes = None

            ret.append(volumes)

        return ret

    def getData(self, meters):
        suffix = "/v2/query/samples"
        if meters[0].startswith("network"):
            resid = list(self.getnetioid(meters[0]))
        ret = list()
        #print meters

        for m in meters:
            tmpret = dict()
            tmpret[m] = dict()
            if m.startswith("network"):
                d = {
                   "filter": '{"and": [{"=": {"counter_name": "%s"}}, {"in": {"resource_id":%s}}]}' % (m, str(resid).replace("'", '"')),
                   "limit": 2 * len(resid)
                   }
            else:
                d = {
                   "filter": '{"and": [{"=": {"counter_name": "%s"}}, {"in": {"resource_id":%s}}]}' % (m, str(self.vm).replace("'", '"').replace("u", "")),
                   "limit": 2 * len(self.vm)
                   }

            #print d
            logging.debug("the payload %s time start at %s ====> %s " % (d, time.strftime("%H:%M:%S"), self.vm))
            resp = self.getCResp(suffix, "post", data=json.dumps(d))
            logging.debug("time done in %s " % time.strftime("%H:%M:%S"))
            if resp:
                for i in resp:
                    inst = i["metadata"]["instance_id"]
                    volume = round(i["volume"], 2)
                    tmpret[m][inst] = [volume]

            ret.append(tmpret)

        return ret

    def cpu(self):
        """return the data point"""
        meters = ["cpu_util"]
        ret = self.getData(meters)

        return ret

    def diskio(self):
        meters = ["disk.read.bytes.rate", "disk.write.bytes.rate"]
        ret = self.getData(meters)

        return ret

    def diskio2(self):
        """
        packets io
        """
        meters = ["disk.read.requests.rate", "disk.write.requests.rate"]
        ret = self.getData(meters)

        return ret

    def mem(self):
        meters = ["memory.usage", "memory"]
        resp = self.getData(meters)
        #pprint(resp)
        ret = {}
        ret["mem_usage"] = {}

        for vm in self.vm:
            try:
                ret["mem_usage"][vm] = [round(resp[0]["memory.usage"][vm][0] / resp[1]["memory"][vm][0], 2)]
            except Exception as e:
                print vm
                ret["mem_usage"][vm] = [0]

        return [ret]

    def netio(self):
        meters = ["network.incoming.bytes.rate", "network.outgoing.bytes.rate"]
        ret = self.getData(meters)

        return ret

    def netio2(self):
        """
        packets io, have no the meters
        """
        meters = ["network.incoming.packets.rate", "network.outgoing.packets.rate"]
        ret = self.getData(meters)

        return ret

    def getnetioid(self, metric):
        """
        get the resource_id of instance
        """
        suffix = "/v2/meters/" + metric
        limit = 2 * len(self.getID().keys())
        suffix = suffix + "?limit=%d" % limit
        #print suffix

        resp = self.getCResp(suffix, "get")
        netid = set()
        for i in self.vm:
            for node in resp:
                if i in node["resource_id"]:
                    netid.add(str(node["resource_id"]))

        return list(netid)

    def getAll(self):
        cpu = self.cpu()
        diskio = self.diskio()
        mem = self.mem()
        netio = self.netio()

        return [cpu, mem, diskio, netio]

class alarm(baseInfo):
    def __init__(self):
        super(alarm, self).__init__()
        self.nagiosURL = self.conf["nagiosURL"]

    def determine(self, vmlis,  data):
        """determine the """
        metric = data[0].keys()[0]
        nodedict = self.getID()
        #print "====>", nodedict

        if metric.startswith("cpu") or metric.startswith("mem"):
            if metric.startswith("cpu"):
                service = "cpu"
            else:
                service = "mem"

            print " the service is ======> %s" % service
            crit = TD["critical"][service]
            warn = TD["warnning"][service]

            vmiter = data[0][metric].keys()
            for vm in vmiter:
                if data[0][metric][vm][0] >= crit:
                    value = data[0][metric].pop(vm)[0]
                    output = self.pluginOut(metric, nodedict[vm], "critical", value)
                    self.send(nodedict[vm], service, 2, output)
                elif data[0][metric][vm][0] >= warn:
                    value = data[0][metric].pop(vm)[0]
                    output = self.pluginOut(metric, nodedict[vm], "warnning", value)
                    self.send(nodedict[vm], service, 1, output)
                else:
                    output = self.pluginOut(metric, nodedict[vm], "ok")
                    self.send(nodedict[vm], service, 0, output)

        elif metric.startswith("net") or metric.startswith("disk"):
            if metric.startswith("net"):
                service = "netio"
                metric0 = "network.incoming.bytes.rate"
                metric1 = "network.outgoing.bytes.rate"
            else:
                service = "diskio"
                metric0 = "disk.read.bytes.rate"
                metric1 = "disk.write.bytes.rate"

            crit = TD["critical"][service]
            warn = TD["warnning"][service]
            inst_crit = {}
            inst_warn = {}
            inst_ok = []
            vmiter = data[0][metric].keys()
            for vm in vmiter:
                if data[0][metric0][vm][0] > crit and data[1][metric1][vm][0] > crit:
                    net_in = data[0][metric0].pop(vm)
                    net_out = data[1][metric1].pop(vm)
                    inst_crit[vm] = ["all", net_in[0], net_out[0]]
                elif data[0][metric0][vm][0] > crit:
                    net_in = data[0][metric0].pop(vm)
                    inst_crit[vm] = ["in", net_in[0]]
                elif data[1][metric1][vm][0] > crit:
                    net_out = data[1][metric1].pop(vm)
                    inst_crit[vm] = ["out", net_out[0]]
                elif data[0][metric0][vm][0] > warn and data[1][metric1][vm][0] > warn:
                    net_in = data[0][metric].pop(vm)
                    net_out = data[1][metric].pop(vm)
                    inst_warn[vm] = ["all", net_in[0], net_out[0]]
                elif data[0][metric0][vm][0] > warn:
                    net_in = data[0][metric0].pop(vm)
                    inst_warn[vm] = ["in", net_in[0]]
                elif data[1][metric1][vm][0] > warn:
                    net_out = data[1][metric1].pop(vm)
                    inst_warn[vm] = ["out", net_out]
                else:
                    inst_ok.append(vm)

            if inst_crit:
               for i,j in inst_crit.items():
                    if j[0] == "all":
                        output = '"the %s in and out is critical,currnet is %s %s"' % (service, j[1], j[2])
                        self.send(nodedict[vm], service, 2, output)
                    elif j[0] == "in":
                        output = '"the %s in is critical,currnet is %s"' % (service, j[1])
                        self.send(nodedict[vm], service, 2, output)
                    elif j[0] == "out":
                        output = '"the %s out is critical,currnet is %s"' % (service, j[1])
                        self.send(nodedict[vm], service, 2, output)

            if inst_warn:
               for i,j in inst_crit.items():
                    if j[0] == "all":
                        output = '"the %s in and out is warnning,currnet is %s %s"' % (service, j[1], j[2])
                        self.send(nodedict[vm], service, 1, output)
                    elif j[0] == "in":
                        output = '"the %s in is warning,currnet is %s"' % (service, j[1])
                        self.send(nodedict[vm], service, 1, output)
                    elif j[0] == "out":
                        output = '"the %s out is warnning,currnet is %s"' % (service, j[1])
                        self.send(nodedict[vm], service, 1, output)
            if inst_ok:
                output = "OK!"
                for vm in inst_ok:
                    self.send(nodedict[vm], service, 0, output)
        return

    def send(self, host, service, state, output):
        """
        send result to nagios
        """
        payload = "cmd_mod=2&cmd_typ=30&host=%s&service=%s&plugin_state=%s&plugin_output=%s" % (host, service, state, output)
        #payload = quote(payload.encode("utf8"))
        print payload
        headers = {
            'content-type': "application/x-www-form-urlencoded"}

        try:
            resp = requests.post(self.nagiosURL, data=payload, headers=headers, timeout=2)
        except Exception as e:
            print "Time out ====>"
            resp = None

        return resp

    @staticmethod
    def pluginOut(metric, host, state, value=None):

        if state in ["critical", "warnning"]:
            ret = '"the metric  %s is %s ,current %s "' % (metric, state, value)
        else:
            ret = "OK"

        return ret

class filesync(object):
    def __init__(self, node, nagios):
        self.node = node
        self.host = nagios

    def diff(self):
        """diff the tpl files"""
        if not os.path.exists("vm.json"):
            with open("vm.json", "w") as wf:
                wf.write(json.dumps([]))

        ret = json.load(open("vm.json"))
        if len(ret) == 0 :
            diff = True
        else:
            diff = False

        if diff:
            with open("vm.json", "w") as wf:
               wf.write(json.dumps(self.node))

            return True
        else:
            return False

    def sync(self):
        """sync the tpl files"""
        nagiostpl = "nagiostpl/"
        if os.path.exists(nagiostpl):
            shutil.rmtree(nagiostpl)

        if not os.path.exists(nagiostpl):
            os.mkdir(nagiostpl)

        ret = json.load(open("vm.json"))
        tpl = open("nagios.tpl").read()
        for k,v in ret.items():
            with open(nagiostpl + k + ".cfg", "w") as wf:
                tplstr = tpl.replace("{{host}}", v.encode("utf8"))
                tplstr = tplstr.replace("{{ID}}", k.encode("utf8"))
                wf.write(tplstr)

        cmd = ["ssh " + self.host + ' "rm -f /etc/nagios3/cvm/*cfg"', "scp nagiostpl/* %s:/etc/nagios3/cvm" % self.host, 'ssh %s "/etc/init.d/nagios3 reload"' % self.host]

        for i in cmd:
            print i
            proc = sp.Popen(i, shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
            proc.wait()

def testceil():
    """
    test ceilometer api
    """
    a = alarm()
    vmlis = ["8eceed13-78f9-47cd-96c4-c7aacdef6332", "2c79bf2e-29b0-41cb-ad8a-86f1a66e1627", "899d0d89-2a9c-43b9-b793-d3fc93842d10"]
    node = a.getID().keys()
    c = ceil(node)
    #pprint(c.cpu())
    #pprint(c.mem())
    #pprint(c.netio())
    #pprint(c.getnetioid("network.incoming.bytes.rate"))
    pprint(c.getAll())
    #m1,m2,m3,m4 = c.getAll()
    #pprint(c.getnetioid("network.incoming.bytes.rate"))


def testtpl():
    a = alarm()
    node = a.getID()
    f = filesync(node)
    if f.diff():
        f.sync()

def main():
    interval = 60
    a = alarm()
    nagios = a.conf["nagios"]

    while True:
        node = a.getID()
        f = filesync(node, nagios)
        if f.diff():
            f.sync()
        c = ceil(node.keys())
        data = c.getAll()
        for i in data:
            a.determine(node, i)

        print "wait 60s"
        #sys.exit(0)
        time.sleep(interval)

if __name__ == "__main__":
    #testceil()
    main()
    #testtpl()
