#!/usr/bin/env python
#coding:utf-8
#author: Chord.deng
###transport the images and volumes between two env in different place
###the document refer to below url
###http://docs.openstack.org/developer/python-novaclient/api.html#usage
###http://docs.openstack.org/developer/python-glanceclient/

from ConfigParser import ConfigParser
from os import path
import keystoneclient.v2_0.client as ksclient
import glanceclient as glclient
import cinderclient.client as cClient
import novaclient.client as nvclient
import subprocess
import requests
#import rados
#import rbd
import sys
import os
import re
import logging
import time
import json

reload(sys)
sys.setdefaultencoding('utf-8')

confFile = "conf.cfg"
now = time.strftime('%Y-%m-%d-%H:%M:%S')

logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='/var/log/translog.log',
                filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('[line:%(lineno)d]:%(levelname)s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

class ky(object):
    """the class of authentication """
    def __init__(self):
        self.remote = "remote"
        self.local = "local"
        self.cf = ConfigParser()
        self.cf.read(confFile)
        self.logFile = "/var/log/trans/trans.log"

    def gIP(self, tgt):
        """extract the ip"""
        ret = self.cf.get(tgt,"OS_AUTH_URL")
        ret = re.split("[:/]",ret)[3]
        return ret

    def getKAuth(self, tgt):
        """get identification information of keystone"""
        try:
            kAuth = {
                "auth_url" : self.cf.get(tgt,"OS_AUTH_URL"),
                "username" : self.cf.get(tgt,"OS_USERNAME"),
                "password" : self.cf.get(tgt,"OS_PASSWORD"),
                "tenant_name" : self.cf.get(tgt,"OS_TENANT_NAME"),
                "insecure" : True}
        except Exception as e:
            logging.critical("配置文件有误")
            logging.critical(e)
            sys.exit(1)

        return kAuth

    def getNAuth(self, tgt):
        """get identification information of nova"""
        try:
            nAuth = {
                "auth_url" : self.cf.get(tgt,"OS_AUTH_URL"),
                "username" : self.cf.get(tgt,"OS_USERNAME"),
                "api_key" : self.cf.get(tgt,"OS_PASSWORD"),
                "project_id" : self.cf.get(tgt,"OS_TENANT_NAME"),
                "direct_use" : False,
                "insecure" : True}
        except Exception as e:
            logging.critical("配置文件有误")
            logging.critical(e)
            sys.exit(1)

        return nAuth

    def getCAuth(self, tgt):
        """get the identification information of cinder"""
        try:
            cAuth = [1,self.cf.get(tgt,"OS_USERNAME"), self.cf.get(tgt,"OS_PASSWORD"),
                    self.cf.get(tgt,"OS_TENANT_NAME"), self.cf.get(tgt,"OS_AUTH_URL")]
        except Exception as e:
            logging.critical("配置文件有误")
            logging.critical(e)
            sys.exit(1)

        return cAuth

    def getTokens(self, tp):
        kAuth = self.getKAuth(self.remote)
        keystone = ksclient.Client(**kAuth)
        url = keystone.service_catalog.url_for(service_type=tp, endpoint_type="publicURL")
        url = url.replace("public.fuel.local", self.gIP(self.remote))
        token = keystone.auth_token

        return url, token

    def rmFile(self, fil):
        """remove the file downloaded"""
        if os.path.isfile(fil) and os.path.exists(fil):
            os.remove(fil)

    def wrFile(self, ids, dic):
        """write the meta data of volumes"""
        fil = self.logFile
        bn = "=" * 10 + ids + "=" * 10 + "\n"
        if os.path.isfile(fil) and os.path.exists(fil):
            with open(fil, "a") as wf:
                wf.write(bn)
                for i,j in dic.iteritems():
                    wf.write("%s : %s\n" %(i,j))
                wf.write("\n\n")
        else:
            print "/var/log/trans/trans.log 日志文件不存在,请创建"

class gl(ky):
    """the class download and upload image"""
    def __init__(self):
        super(gl, self).__init__()
        self.gClientR = self.getGlanceClient(self.remote)
        self.gClientL = self.getGlanceClient(self.local)

    def getGlanceClient(self, tgt):
        """get the GlanceClient for access glance api"""
        kAuth = self.getKAuth(tgt)
        keystone = ksclient.Client(**kAuth)
        logging.debug("the %s token is %s"  %(tgt, keystone.auth_token))
        glEnd = keystone.service_catalog.url_for(service_type="image", endpoint_type="publicURL")
        glEnd = glEnd.replace("public.fuel.local", self.gIP(tgt))
        logging.debug("the glance endpoint is %s" %glEnd)
        glCli = glclient.Client("1", glEnd, token=keystone.auth_token, insecure=True)

        return glCli

    def getImgLis(self):
        """extract the images list local server need sync"""
        try:
            cfImg = self.cf.get(self.local, "IMAGE_ID")
        except Exception as e:
            logging.critical("IMAGE_ID配置有误")
            logging.critical(e)
            sys.exit(1)

        imgLisL = [im.to_dict() for im in self.gClientL.images.list()]
        imgLisR = [im.to_dict() for im in self.gClientR.images.list()]
        imR = [im["checksum"] for im in imgLisR]

        try:
            if cfImg == "ALL":
                imgLis = cfImg.split(",")
                imgLis = [im for im in imgLisL if im["checksum"] not in imR]
                logging.debug("=======the imgList")
                logging.debug([im["id"] for im in imgLis])

            elif cfImg.startswith("!"):
                eximg = cfImg[1:].split(",")
                imgLis = [im for im in imgLisL if im["id"] not in eximg]
                imgLis = [im for im in imgLis if im["checksum"] not in imR]
                logging.debug("=======the imgList")
                logging.debug([im["id"] for im in imgLis])

            else:
                imgLis = cfImg.split(",")
                imgLis = [im for im in imgLisL if im["id"] in imgLis]
                imgLis = [im for im in imgLis if im["checksum"] not in imR]
                logging.debug("=======the imgList")
                logging.debug([im["id"] for im in imgLis])

        except Exception as e:
            logging.critical("获取img列表失败")
            logging.critical(e)
            sys.exit(1)

        return imgLis

    def saveImage(self):
        """download the image to local disk"""
        imgLis = self.getImgLis()
        self.imgLis = imgLis

        for im in imgLis:
            fName = im["name"]
            saveName = "-".join(im["name"].split())
            imdata = self.gClientL.images.data(im["id"])

            with open(saveName,"wb") as wf:
                logging.info("下载镜像 %s" % fName)
                for chk in imdata.iterable:
                    wf.writelines(chk)

    def uploadImage(self):
        """upload the image to local glance serveice"""
        if self.imgLis:
            for im in self.imgLis:
                fName = im["name"]
                saveName = "-".join(im["name"].split())
                fNameTest = im["name"] + "test2"
                with open(saveName) as fimage:
                    try:
                        logging.info("上传镜像 %s" %fName)
                        self.gClientR.images.create(name=fName, is_public=im["is_public"],
                                       disk_format=im["disk_format"],
                                       container_format=im["container_format"], data=fimage)
                        time.sleep(0.5)
                    except Exception as e:
                        logging.critical("镜像 %s 上传失败" %fName)
                        logging.critical(e)
                        sys.exit(1)
                    finally:
                        self.rmFile(saveName)
        else:
            logging.info("没有需要备份的镜像")


    def delIMG(self, ImgID):
        "delete the images after image converted"
        logging.info("delete the image %s" % ImgID)
        img = self.gClientR.images.get(ImgID)
        img.delete()

    def uploadImageTest(self):
        """upload test"""
        with open("test.img") as fimage:
            self.gClientR.images.create(name="myimage2", is_public=False, disk_format="qcow2",
                       container_format="bare", data=fimage)

class nv(ky):
    """the class for nova api"""
    def __init__(self):
        super(nv, self).__init__()
        self.nClientL = self.getNovaClient(self.local)
        self.nClientR = self.getNovaClient(self.remote)

    def getNovaClient(self, tgt):
        nAuth = self.getNAuth(tgt)
        nvCli = nvclient.Client(2, **nAuth)

        return nvCli

    def getInfo(self, ids, tp):
        if tp == "compute":
            info = self.nClientL.servers.get(ids)._info
        elif tp == "volume":
            info = self.nClientL.volumes.get(ids)._info
        else:
            info = None

        return info

    def getSize(self, flavorID):
        flavorID = self.nClientL.flavors.get(flavorID).disk

        return flavorID

class ci(ky):
    """the class for cinder api"""
    def __init__(self):
        super(ci, self).__init__()
        self.cClientL = self.getCinderClient(self.local)
        self.cClientR = self.getCinderClient(self.remote)

    def getCinderClient(self, tgt):
        cAuth = self.getCAuth(tgt)
        cinder = cClient.Client(*cAuth, insecure=True, retries=3)

        return cinder

    def getInfo(ids):
        vol = self.cClientL.get(ids)
        volInfo = vol._info

        return volInfo

class req(ky):
    """the class for openstack restful api"""
    def __init__(self):
        super(req, self).__init__()
        headers = {}
        headers["Content-Type"] = "application/json"
        self.headers = headers
        url,token = self.getTokens("volumev2")
        self.url = url + "/volumes"
        self.token = token
        self.headers["X-Auth-Token"] = token


    def pVol(self, size, name, description, imgID):
        data = {"volume":{"size":size,
                          "name":name,
                          "description":description,
                          "imageref":imgID}}

        data = json.dumps(data)
        ret = requests.post(self.url, data=data, headers=self.headers, verify=False)

        return ret.json()

    def gVol(self, ids):
        url = "%s/%s" %(self.url, ids)
        ret = requests.get(url, headers=self.headers, verify=False)

        if ret.reason == "OK":
            ret = ret.json()

        return ret

class ce(ky):
    """the class for manipulate volumes"""
    def __init__(self):
        super(ce, self).__init__()
        self.cluster = rados.Rados(conffile="/etc/ceph/ceph.conf")
        self.cluster.connect()
        self.ioctxRC = self.cluster.open_ioctx("compute")
        self.ioctxRV = self.cluster.open_ioctx("volumes")
        self.readConf()
        self.gl = gl()
        self.nv = nv()
        self.req = req()
        self.nC = self.nv.nClientR
        self.nCL = self.nv.nClientL
        self.gC = self.gl.gClientR
        self.gCL = self.gl.gClientL
        self.cephCIDS, self.cephVIDS = self.getCephIDS(self.cIDS, self.vIDS)

    def testInfo(self):
        """just test ceph"""
        print "librados version: " + str(self.cluster.version())
        print "Will attempt to connect to: " + str(self.cluster.conf_get('mon initial members'))

    def readConf(self):
        """read the volume id from config file"""
        try:
            self.cIDS = self.cf.get(self.local,"COMPUTE_VOLUME_ID")
            self.cIDS = [i.strip() for i in self.cIDS.split(",")]
        except Exception as e:
            logging.critical("没有配置COMPUET_VOLUME_ID")
            logging.critical(e)
            sys.exit(1)

        try:
            self.vIDS = self.cf.get(self.local,"VOLUME_ID")
            self.vIDS = [i.strip() for i in self.vIDS.split(",")]
        except Exception as e:
            logging.critical("没有配置VOLUME_ID")
            logging.critical(e)
            sys.exit(1)

    def getCephIDS(self, cVolIDS, volIDS):
        rbdS = rbd.RBD()
        cephCIDS = [ids + "_disk" for ids in cVolIDS if ids + "_disk" in rbdS.list(self.ioctxRC)]
        cephVIDS = ["volume-" + ids for ids in volIDS if "volume-" + ids in rbdS.list(self.ioctxRV)]

        return cephCIDS, cephVIDS


    def execALl(self):
        """execAll task"""
        logging.debug("遍历cephCIDS")
        logging.debug(self.cephCIDS)

        if self.cephCIDS:
            for ID in self.cephCIDS:
                cID = ID[:-5]
                cIDInfo = self.nv.getInfo(cID,"compute")
                cIDSize = self.nv.getSize(cIDInfo["flavor"]["id"])
                if cIDSize == 0:cIDSize =1
                logging.debug("save and upload %s" %cID)
                self.saveUpload(ID, cIDInfo, cIDSize, "compute")
        else:
           print "没有需要同步的compute volume"

        if self.cephVIDS:
            for ID in self.cephVIDS:
                vID = ID[7:]
                vIDInfo = self.nv.getInfo(vID,"volume")
                vIDSize = vIDInfo["size"]
                if vIDSize == 0:vIDSize =1
                logging.debug("save and upload %s" %vID)
                self.saveUpload(ID, vIDInfo, vIDSize, "volumes")
        else:
           print "没有需要同步的volume"

        logging.info("所有操作已完成")


    def saveUpload(self, cephID, volInfo, size, cephPool):
        """upload the downloaded volumes as image and convert the image to volume"""
        ID = cephID
        info = volInfo
        tp = cephPool
        descr = "None"
        if tp == "volumes":
           descr = info["display_description"]
        cmdStr = "rbd export -p %s %s %s"
        if tp == "volumes":
            saveName = info["display_name"]
        else:
            saveName = info["name"]
        saveName = "-".join(saveName.split()) + now
        if tp == "volumes":
            displayName = info["display_name"] + now
        else:
            displayName = info["name"] + now
        cmd = cmdStr %(tp, ID, saveName)

        try:
            logging.info("download volume %s" % ID )
            logging.debug("执行命令 %s " %cmd)
            p = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            retCode = p.wait()
            logging.debug("执行结果:%s" %retCode)
        except Exception as e:
            logging.critical("执行 %s 失败" % cmd)
            logging.critical(e)
            sys.exit(1)

        logging.info("上传volume %s 作为镜像" %info["id"])

        if not retCode:
            with open(saveName) as fimage:
                try:
                    logging.info("上传volume %s 作为 %s镜像" % (ID, saveName))
                    self.gC.images.create(name=displayName, is_public=True,
                                   disk_format="raw",
                                   container_format="bare", data=fimage)

                except Exception as e:
                    logging.critical("volume %s 上传失败" % ID)
                    logging.critical(e)
                    sys.exit(1)
                finally:
                    self.rmFile(saveName)

            logging.debug("将镜像:%s 转换为 volume" %displayName)
            img = self.gC.images.find(name=saveName)._info

            if tp == "volumes":
                try:
                    resp = self.req.pVol(size=size, name=displayName, description=descr, imgID=img["id"])
                    vid = resp["volume"]["id"]
                    try:
                        vStatus = self.req.gVol(vid)["volume"]["status"]
                        print "上传中....",
                        while vStatus != "available":
                            time.sleep(1)
                            vStatus = self.req.gVol(vid)["volume"]["status"]
                            print ".",

                        print "\n"
                        print "上传成功!!!"
                    except Exception as e:
                        logging.warning("获取image状态失败")
                        time.sleep(3)

                    logging.info("开始记录volume:%s 元数据信息" %ID)
                    self.wrFile(cephID, info)
                except Exception as e:
                    logging.critical("镜像:%s 转换失败" % img["name"])
                    logging.critical(e)
                    sys.exit(1)
                finally:
                    self.gl.delIMG(img["id"])
                    pass
            else:
                logging.info("开始记录volume:%s 元数据信息" %ID)
                self.wrFile(cephID, info)
                print "上传成功!!!"

        else:
            logging.info("执行命令: %s 失败" % cmd )
            sys.exit(1)

def main():
    confFile = sys.argv[1]

    if not path.isfile(confFile):
        logging.critical("配置文件不存在")
        sys.exit(1)

    print '\033[1;34;40m'
    print '*' * 50
    print "开始同步镜像"
    print '\033[0m'
    glan= gl()
    glan.saveImage()
    glan.uploadImage()
    print "\033[1;32;40m镜像同步完成 \033[0m"

    print '\033[1;34;40m'
    print '*' * 50
    print "开始同步Volume"
    print '\033[0m'
    cep = ce()
    cep.execALl()
    print "\033[1;32;40m Volume 同步完成 \033[0m"

if __name__ == "__main__":
    main()
    #ceC = ce()
    #ceC.testInfo()
