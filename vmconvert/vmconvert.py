#!/usr/bin/env python
#coding: utf-8
import logging
import re
import time
from multiprocessing import Pool
import sys
from ConfigParser import ConfigParser
import requests
import json
from pprint import pprint
import csv
import signal
import os
from os import path
import paramiko
from Queue import Queue

# the qvm is the queue for the vm is not downloaded
qvm = Queue()
# the qdown is queue for vm has downloaded
qdown = Queue()



def InitLog(filename, console=True):
    logger = logging.getLogger(filename)
    logger.setLevel(logging.DEBUG)

    logpath = "/var/log/vmconvert/" + filename + ".log"
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


def diskusage(path, unit=None):
    d = os.statvfs(path)
    freeDisk = d.f_bavail * d.f_frsize

    if unit == "KB":
        freeDisk = freeDisk / 1024
    elif unit == "MB":
        freeDisk = freeDisk / (1024 * 1024)
    elif unit == "GB":
        freeDisk = freeDisk / (1024 * 1024 * 1024)

    return freeDisk


def tryencode(name):
    try:
        name = name.decode("gbk").encode("utf8")
        return name
    except Exception as e:
        return name


class shex(object):
    def __init__(self, exsi, exsipass, vmname, logfile):
        self.exsi = exsi
        self.exsipass = exsipass
        self.vmname = vmname
        self.logfile = logfile

    def writepass(self):
        with open(".esxpasswd", "w") as wf:
            wf.write(self.exsipass)

    def VirtDown(self):
        """download the vmdk file to local system"""
        self.logfile.info("Download command start.....")
        from sh import virt_v2v_copy_to_local
        self.writepass()
        cmd = "virt-v2v-copy-to-local -v -ic esx://root@%s?no_verify=1 --password-file .esxpasswd %s"
        cmd = cmd % (self.exsi, self.vmname)
        cmd = cmd.split()[1:]
        stderrfilename = self.vmname + ".output"

        try:
            self.logfile.info("Excute command: %s" % cmd)
            self.logfile.info("Download vm: %s" % self.vmname)
            proc = virt_v2v_copy_to_local(*cmd, _iter=True, _err=stderrfilename)
        except Exception as e:
            self.logfile.critical("Excute command faild: %s " % cmd)
            self.logfile.critical(e)
            return None

        msg = "Download the vmdk:%s from exsi:%s " % (self.vmname, self.exsi)
        self.logfile.info(msg)
        for line in proc:
            self.logfile.info(line)
            length = shex.getLength(stderrfilename)
            if length:
                msg = "VMDK size is Length: %s " % length
                self.logfile.info(msg)
                sysdisk = diskusage("./")
                with open(stderrfilename, "w") as wf:
                    wf.truncate()
                if length * 1.5 > sysdisk:
                    self.logfile.critical("WTF the disk usage")
                    self.logfiel.critical("Try to kill the process and delete the vmdk")
                    proc.process.signal(signal.SIGINT)
                    self.logfile.critical("the vm is too big!!!!")
                    self.remove(self.vmname)
                    return None

        msg = "Command return code: %s" % proc.exit_code
        self.logfile.info(msg)

        ret = not proc.exit_code

        if ret:
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
                self.logfile.info("Download completed")
            open(".vm/" + self.vmname + ".download", "a").close()
        else:
            msg = "Download faild for some reasone, excute the command manually for review: %s " % cmd
            self.logfile.info()

        return ret

    def VirtConvert1(self, out="./"):
        """"convert the vm to qcow2 format with virt-v2v"""
        self.logfile.info("Convert1 command start.....")
        from sh import virt_v2v
        vm = self.vmname + "-disk1"
        cmd = "virt-v2v -v -i disk %s -of qcow2 -o local -os %s "
        cmd = cmd % (vm, out)
        cmd = cmd.split()[1:]

        try:
            self.logfile.info("Excute command: %s" % cmd)
            self.logfile.info("Convert vm: %s" % self.vmname)
            proc = virt_v2v(*cmd, _iter=True)
        except Exception as e:
            self.logfile.critical("Excute command failed: %s " % cmd)
            self.logfile.critical(e)
            return False

        for line in proc:
            self.logfile.info(line)

        ret = not proc.exit_code

        if ret:
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
            self.logfile.info("Converte completed.....")
            open(".vm/" + self.vmname + ".convert", "a").close()
            os.rename(vm + "-sda", vm[:-6] + "-qcow2")
            self.logfile.info("Remove the original vmdk file")
            tmpret = shex.remove(vm)
            if tmpret:
                self.logfile.info("Remove the original vmdk file failed")
                self.logfile.critical(tmpret)
        return ret

    def VirtConvert2(self, out="./"):
        """"convert the vm to qcow2 format with qemu-img"""
        self.logfile.info("Convert1 command start.....")
        from sh import qemu_img
        vm = self.vmname + "-disk1"
        cmd = "qemu-img convert -O qcow2 %s %s%s-qcow2"
        cmd = cmd % (vm, out, self.vmname)
        cmd = cmd.split()[1:]

        try:
            self.logfile.info("Excute command: %s" % cmd)
            self.logfile.info("Convert vm: %s" % self.vmname)
            proc = qemu_img(*cmd, _iter=True)
        except Exception as e:
            self.logfile.critical("Excute command failed: %s " % cmd)
            self.logfile.critical(e)
            return False

        for line in proc:
            self.logfile.info(line)

        ret = not proc.exit_code

        if ret:
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
            self.logfile.info("Converte completed.....")
            open(".vm/" + self.vmname + ".convert", "a").close()
            self.logfile.info("Remove the original vmdk file")
            tmpret = shex.remove(vm)
            if tmpret:
                self.logfile.info("Remove the original vmdk file failed")
                self.logfile.critical(tmpret)
        return ret

    def poweroff(self, release, server, username, password):
        """try poweroff the vm"""
        if release.lower() != "windows":
            if release == "centos6" or release == "redhat7":
                try:
                    self.cleanNet(release, server, username, password)
                    ret = self.shutdown(server, username, password)
                    time.sleep(10)
                except Exception as e:
                    msg = "Poweroff failed....."
                    self.logfile.critical(msg)
                    self.logfile.critical(e)
                    return False

            else:
                try:
                    ret = self.shutdown(server, username, password)
                    time.sleep(10)
                except Exception as e:
                    msg = "Poweroff failed....."
                    self.logfile.critical(msg)
                    self.logfile.critical(e)
                    return False
            return ret

    @staticmethod
    def getLength(fname):
        """get the vm disk size"""
        lengthre = re.compile(r"Content-Length: (\d+)")
        length = None
        with open(fname) as rf:
            retline = rf.read()
            length = lengthre.findall(retline)
            if len(length) > 0:
                length = int(length[0])

        return length

    @staticmethod
    def remove(fname):
        """remove the vm fiel"""
        if path.isfile(fname):
            try:
                os.remove(fname)
                return None
            except Exception as e:
                return e
        else:
            msg = "Not a file: %s" % fname
            return msg

    def cleanNet(self, release, server, username, password):
        """clean up the network configuration"""
        command7 = """cp /etc/sysconfig/network-scripts/ifcfg-eth0 /root/ifcfg-eth0;echo "TYPE=Ethernet
BOOTPROTO=dhcp
NAME=eth0
DEVICE=eth0
ONBOOT=yes" > /etc/sysconfig/network-scripts/ifcfg-eth0
"""
        command6 = """cp /etc/sysconfig/network-scripts/ifcfg-eth0 /root/ifcfg-eth0;echo "DEVICE=eth1
TYPE=Ethernet
ONBOOT=yes
BOOTPROTO=dhcp" > /etc/sysconfig/network-scripts/ifcfg-eth0
"""
        if release == "centos6":
            command = command6
        elif release == "redhat7":
            command = command7

        ret = self.sshcommand(server, username, password, command)

        return ret

    def shutdown(self, server, username, password):
        """shutdown the server"""
        command = "shutdown -h now"

        ret = self.sshcommand(server, username, password, command)

        return ret

    def sshcommand(self, server, username, password, command):
        """ssh in the server and execute command """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(server, username=username, password=password, timeout=5)
        except Exception as e:
            msg = "the server:%s use username:%s,password:%s connect faild" % (server, username, password)
            self.logfile.critical(msg)
            self.logfile.critical(e)
            return None

        try:
            _, stdout, stderr = ssh.exec_command(command)
        except Exception as e:
            msg = "execute command:%s faild" % command
            self.logfile.critical(e)
            return None
        finally:
            ssh.close()

        return True

    @staticmethod
    def checkRecord(vmname, method):
        """check the file is downloaded or upload"""
        if method == "download":
            fpath = ".vm/" + vmname + ".download"
            ret = os.path.exists(fpath)
        elif method == "convert":
            fpath = ".vm/" + vmname + ".convert"
            ret = os.path.exists(fpath)
        else:
            print "Fuck you imput"
            ret = False

        return ret

    @staticmethod
    def writesuffix(logfile, fname, suffix):
        if not os.path.exists(".vm"):
            os.mkdir(".vm")
            logfile.info("Download completed")
            open(".vm/" + fname + suffix, "a").close()


class base(object):
    """init the info of all compute, and get the token for access the api"""

    def __init__(self, logfile):
        confFile = sys.argv[1]

        headers = {}
        headers["Content-Type"] = "application/json"

        self.cf = ConfigParser()
        self.cf.read(confFile)
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

    def pre(self):
        """read the config file for init"""

        try:
            sec = self.cf.sections()
        except Exception as e:
            self.logfile.critical(e)
            self.logfile.critical("配置文件有误,没有配置[openstack],[vm],[vmware]段落")
            sys.exit(1)

        secLis = ['openstack', 'multiprocess', 'vm']
        openLis = ["auth_url", "uname", "passwd", "tenant"]
        vmLis = ["path"]

        testsec = [s for s in secLis if s in sec]
        if len(testsec) != 3:
            self.logfile.critical("配置文件有误,没有配置[openstack],[vm],[vmware]某一段落")
            sys.exit(1)

        for i in openLis:
            if i not in self.cf.options("openstack"):
                self.logfile.critical("配置文件有误,没有配置[openstack]段落,或缺少相关配置信息")
                sys.exit(1)

        for i in vmLis:
            if i not in self.cf.options("vm"):
                self.logfile.critical("配置文件有误,没有配置[vm]段落,或缺少相关配置信息")
                sys.exit(1)

        return True

    def getToken(self):
        headers = self.headers
        url = self.conf["auth_url"] + "/tokens"
        data = '{"auth": {"tenantName": "%s", "passwordCredentials": {"username": "%s", "password": "%s"}}}'
        data = data % (self.conf["tenant"], self.conf["uname"], self.conf["passwd"])

        try:
            msg = "Acquire token from %s " % self.conf["auth_url"]
            self.logfile.debug(msg)
            ret = requests.post(url, data=data, headers=headers)
            ret = ret.json()
        except Exception as e:
            msg = "Acuire Token failed \n data: %s \n headers: %s" % (data, headers)
            self.logfile.critical(msg)
            self.logfile.critical(e)

        catalog = ret["access"]["serviceCatalog"]
        token = ret["access"]["token"]["id"]

        return catalog, token

    def getResp(self, suffix, method, data=None, headers=None, params=None, isjson=True, api="nova"):
        """return the result of requests"""
        apiURL = self.getURL(self.catalog, api)
        url = apiURL + suffix
        if headers is None:
            headers = self.headers.copy()
        headers["X-Auth-Token"] = self.token

        req = getattr(requests, method)
        try:
            ret = req(url, data=data, headers=headers, params=params, verify=False)
            #print ret.url
            #print ret.content
            self.logfile.debug("request url:%s" % ret.url)
            if ret.status_code == 401:
                self.logfile.warning("Token expired, acquire token again")
                self.catalog, self.token = self.getToken()
                headers["X-Auth-Token"] = self.token
                self.logfile.debug("Request headers:%s" % ret.request.headers)
                ret = req(url, data=data, headers=headers)

            if isjson:
                ret = ret.json()
        except Exception as e:
            msg = "The method:%s for path:%s failed \ndata:%s \nheaders:%s" % (method, suffix, data, headers)
            self.logfile.critical(msg)
            self.logfile.critical(e)
            sys.exit(1)
            ret = None

        return ret


class opCli(base):
    """the openstack rest api client """
    def __init__(self, logfile):
        super(opCli, self).__init__(logfile)

    def createImg(self, name, contf="bare", diskf="qcow2"):
        """create the img"""
        suffix = "/v2/images"

        data = {}
        data["container_format"] = contf
        data["disk_format"] = diskf
        data["name"] = name

        data = json.dumps(data)
        resp = self.getResp(suffix, "post", data=data, api="glance")

        return resp

    def uploadImg(self, imgPath, imgFile, vmname):
        """upload the image to openstack glance service"""
        suffix = imgPath
        headers = {'content-type': "application/octet-stream"}
        headers["X-Auth-Token"] = self.token
        apiURL = self.getURL(self.catalog, "glance")

        url = "".join([apiURL, suffix])

        with open(imgFile) as img:
            req = requests.put(url, headers=headers, data=img)

        if req.status_code == 204:
            ret = "ok"
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
                open(".vm/" + vmname + ".upload", "a").close()

            tmpret = shex.remove(imgFile)
            if tmpret:
                self.logfile.critical(tmpret)
        else:
            self.logfile.critical("upload abnormally")
            self.logfile.critical(req.content)
            ret = req.content

        return ret

    def boot(self, name, imgRef, flavorRef, netRef):
        """boot the instance with specific img and network"""
        suffix = "/servers"
        server = {}
        data = {}
        server["name"] = name
        server["flavorRef"] = flavorRef
        server["imageRef"] = imgRef
        server["networks"] = []
        server["networks"].append({"uuid": netRef})
        data["server"] = server

        data = json.dumps(data)
        resp = self.getResp(suffix, "post", data=data)

        return resp

    def addFlotingIP(self, serID, ip):
        """add"""
        suffix = "/servers/%s/action" % serID
        data = {}
        data["addFloatingIp"] = {}
        data["addFloatingIp"]["address"] = ip

        data = json.dumps(data)
        resp = self.getResp(suffix, "post", data=data)

        return resp

    def listNet(self):
        """get the uuid"""
        suffix = "/v2.0/networks"

        resp = self.getResp(suffix, "get", api="neutron")

        return resp

    def listFlavor(self):
        """list the flavor"""
        suffix = "/flavors/detail"

        resp = self.getResp(suffix, "get")

        return resp

    def createFlavor(self, vmmem, vmcpu, vmdisk):
        """create the flavor"""
        suffix = "/flavors"
        name = "convert" + time.strftime("%Y-%m-%d-%H:%M")
        data = {}
        data["flavor"] = {}
        data["flavor"]["name"] = name
        data["flavor"]["ram"] = vmmem
        data["flavor"]["vcpus"] = vmcpu
        data["flavor"]["disk"] = vmdisk

        data = json.dumps(data)
        resp = self.getResp(suffix, "post", data=data)

        ret = resp["flavor"]["id"]

        return ret


def download():
    """download the vmdk file and convert"""
    empty = qvm.empty()
    msg = "the vm of Queue empty is %s" % empty
    print msg
    while not qvm.empty():
        ret = False
        vm = qvm.get()
        logfile = InitLog(vm[7], console=True)
        logfile.info("===Download Process start===")
        logfile.info("get the infomation: %s" % vm)

        try:
            vmrelease,vmuser,vmpass,vmip,exsiip,exsiuser,exsipass,vmname,vmmem,vmcpu,vmdisk,vmowner,vmproject,multidisk = vm
            vmowner = tryencode(vmowner)
            #print vmrelease
        except Exception as e:
            msg = "The vm data is wrong: %s " % vm
            logfile.critical(msg)
            logfile.critical(e)
            shex.writesuffix(logfile, vmname, ".wrong")
            continue

        shx = shex(exsiip, exsipass, vmname, logfile)
        msg = "Check if the vm have been downloaded: %s" % vmname
        logfile.info(msg)
        downloaded = shx.checkRecord(vmname, "download")
        if not downloaded:
            shx.poweroff(vmrelease, vmip, vmuser, vmpass)
            ret = shx.VirtDown()
            if not ret:
                msg = "Download faild ===> %s" % vm[7]
                logfile.info(msg)
                shex.writesuffix(logfile, vmname, ".wrong")
                continue

        if vmrelease.lower() == "ubuntu":
            if not shx.checkRecord(vmname, "convert"):
                ret = shx.VirtConvert2()
        else:
            if not shx.checkRecord(vmname, "convert"):
                ret = shx.VirtConvert1()

        if ret:
            logfile.info("Put the converted vm to the queue for upload.....")
            qdown.put(vm)
            logfile.info("Put done...")
        else:
            logfile.critical("Converted failed!!!")
            shex.writesuffix(logfile, vmname, ".wrong")


def upload():
    """upload the converted image and boot a server from the image"""
    empty = qdown.empty()
    msg = "the downloaded vm of Queue empty is %s" % empty
    print msg
    while True:
        vm = qdown.get()
        vmrelease,vmuser,vmpass,vmip,exsiip,exsiuser,exsipass,vmname,vmmem,vmcpu,vmdisk,vmowner,vmproject,multidisk = vm
        vmowner = tryencode(vmowner)

        logfile = InitLog(vmname, console=True)
        logfile.info("===UPload Process start===")
        logfile.info("Get the infomation: %s" % vm)

        if shex.checkRecord(vmname, ".wrong"):
            logfile.info("The vm is wrong,skip this")
            continue

        op = opCli()
        imgfile = vmname + "-qcow2"
        msg = "Create the image from the vm file: %s" % vmname
        logfile.info(msg)
        img = op.createImg(vmname)
        if img:
            msg = "The image create: %s" % vmname
            logfile.info(msg)
        else:
            logfile.critical("Image create failed!!!")
            shex.writesuffix(logfile, vmname, ".wrong")
            continue

        imgPath = img["file"]
        imgID = img["id"]

        logfile.info("UPload image")
        uploadRet = op.uploadImg(imgPath, imgfile, vmname)
        if uploadRet == "ok":
            logfile.info("UPload completed")
            shex.writesuffix(logfile, vmname, ".upload")
        else:
            logfile.critical("UPload failed")
            logfile.critical(uploadRet)
            shex.writesuffix(logfile, vmname, ".wrong")
            continue

        try:
            ext_vlan = "MC_VLAN_10.2." + vmip.split(".")[2]
            fix_vlan = op.cf.get(ext_vlan, "fix")
        except Exception as e:
            logfile.critical("The network is invalid")
            logfile.error(e)
            logfile.critical("Network invail!!!")
            shex.writesuffix(logfile, vmname, ".wrong")
            continue

        networklis = op.listNet()["networks"]
        network = [net["id"] for net in networklis if net["name"] == fix_vlan][0]

        flavorlis = op.listFlavor()["flavors"]
        flavor = [[f["id"], f["ram"], f["vcpus"], f["disk"]] for f in flavorlis if f["ram"] >= vmmem and f["vcpus"] >= vmcpu and f["disk"] >= vmdisk]
        if len(flavor) > 1:
            flavor.sort(key=lambda x: x[3])
            flavor = flavor[0][0]
        elif len(flavor) == 0:
            flavor = op.creatFlavor(vmmem, vmcpu, vmdisk)
        else:
            flavor = flavor[0][0]

        instance = "-".join([vmowner, vmname])
        server = op.boot(instance, imgID, flavor, network)

        if server:
            if server.status_code == 202:
                logfile.info("Boot the image success!!!")
            else:
                logfile.critical("Boot the image failed")
                shex.writesuffix(logfile, vmname, ".wrong")
                continue
        else:
            logfile.critical("Boot the image failed")
            shex.writesuffix(logfile, vmname, ".wrong")
            continue

        serverID = server["server"]["id"]
        floatingip = op.addFlotingIP(serverID, vmip)

        if floatingip:
            if floatingip.status_code == 202:
                logfile.info("Add floationgip success!!!")
            else:
                logfile.critical("Add floationgip  failed")
                shex.writesuffix(logfile, vmname, ".wrong")
                continue
        else:
            logfile.critical("Add floationgip  failed")
            shex.writesuffix(logfile, vmname, ".wrong")


def batch(action, size, *args):
    """batch run the action for higher performance"""
    #print action,size,args
    p = Pool(size)
    for i in range(size):
        p.apply_async(action)

    return p


def testvmware():
    log = InitLog("test.log", console=True)
    with open("test.csv") as rf:
        csvRead = csv.reader(rf)
        csvRet = [line for line in csvRead]
        retDict = {}
        retDict["release"] = csvRet[1][0]
        retDict["vmip"] = csvRet[1][3]
        retDict["exsi"] = csvRet[1][4]
        retDict["exsipass"] = csvRet[1][6]
        retDict["vmname"] = csvRet[1][7]
        retDict["owner"] = csvRet[1][12]
        retDict["group"] = csvRet[1][13]
        #retDict["mem"] = csvRet[1][14]
        #retDict["cpu"] = csvRet[1][15]

    print retDict
    sh = shex(retDict["exsi"], retDict["exsipass"], retDict["vmname"], log)
    #test vmdk file download
    sh.VirtDown()
    #test vmdk convert
    #sh.VirtConvert1()
    #sh.VirtConvert2()


def testopenstack():
    log = InitLog("test.log", console=True)
    #test opCli class initialize
    with open("test.csv") as rf:
       csvRead = csv.reader(rf)
       csvRet = [line for line in csvRead]
       retDict = {}
       retDict["release"] = csvRet[1][0]
       retDict["vmip"] = csvRet[1][3]
       retDict["exsi"] = csvRet[1][8]
       retDict["exsipass"] = csvRet[1][9]
       retDict["vmname"] = csvRet[1][11]
       retDict["owner"] = csvRet[1][12]
       retDict["group"] = csvRet[1][13]
       retDict["mem"] = csvRet[1][14]
       retDict["cpu"] = csvRet[1][15]

    op = opCli()
    #test img create
    #img = op.createImg("testvm")

    #get created image file path and id
    #imgfile = img["file"]
    #imgID = img["id"]

    #test upload img
    #print op.uploadImg(imgfile, "testvm.qcow2")


    #test boot server
    #server = op.boot("testvmfortest", imgID, "1", "541b6469-c0f9-4743-a756-66bcbc39d299")
    #serverID = server["server"]["id"]

    #test list Network and list Flavor
    pprint(op.listNet())
    pprint(op.listFlavor())


def testdownload():
    if len(sys.argv) < 2:
        print "没有指定配置文件,启动失败"

    prelog = InitLog("pre")

    op = opCli(prelog)
    csvformat = ['vmrelease','vmuser','vmpass','vmip','exsiip','exsiuser','exsipass','vmname','vmmem','vmcpu','vmdisk','vmowner','vmproject','multidisk']
    #print csvformat
    if not op.pre():
        print "配置文件有误"
        sys.exit(1)

    csvfile = op.cf.get("vm", "path")
    with open(csvfile) as rf:
        csvreader = csv.reader(rf)
        header = csvreader.next()
        #print header
        if header == csvformat:
            for line in csvreader:
                #print "====>line", line
                qvm.put(line)
                #print "====>empty", qvm.empty()
        else:
            print "虚拟机列表文件有误"
            sys.exit(1)

    download()
    print "Download done...."


def testupload():
    if len(sys.argv) < 2:
        print "没有指定配置文件,启动失败"

    prelog = InitLog("pre")

    op = opCli(prelog)
    csvformat = ['vmrelease','vmuser','vmpass','vmip','exsiip','exsiuser','exsipass','vmname','vmmem','vmcpu','vmdisk','vmowner','vmproject','multidisk']
    #print csvformat
    if not op.pre():
        print "配置文件有误"
        sys.exit(1)

    csvfile = op.cf.get("vm", "path")
    with open(csvfile) as rf:
        csvreader = csv.reader(rf)
        header = csvreader.next()
        #print header
        if header == csvformat:
            for line in csvreader:
                #print "====>line", line
                qdown.put(line)
                #print "====>empty", qvm.empty()
        else:
            print "虚拟机列表文件有误"
            sys.exit(1)

    upload()
    print "Download done...."


def main():
    if len(sys.argv) < 2:
        print "没有指定配置文件,启动失败"

    prelog = InitLog("pre")

    op = opCli(prelog)
    csvformat = ['vmrelease','vmuser','vmpass','vmip','exsiip','exsiuser','exsipass','vmname','vmmem','vmcpu','vmdisk','vmowner','vmproject','multidisk']
    #print csvformat
    if not op.pre():
        print "配置文件有误"
        sys.exit(1)

    csvfile = op.cf.get("vm", "path")
    with open(csvfile) as rf:
        csvreader = csv.reader(rf)
        header = csvreader.next()
        #print header
        if header == csvformat:
            for line in csvreader:
                qvm.put(line)
        else:
            print "虚拟机列表文件有误"
            sys.exit(1)

    cf = ConfigParser()
    cf.read(sys.argv[1])
    downSize = cf.getint("multiprocess", "download")
    upSize = cf.getint("multiprocess", "upload")
    downloadProc = batch(download, downSize)
    uploadProc = batch(upload, upSize)

    downloadProc.close()
    uploadProc.close()
    downloadProc.join()
    uploadProc.join()

if __name__ == "__main__":
   #main()
   testdownload()
   #testvmware()
