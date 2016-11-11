#!/usr/bin/env python
#coding: utf-8

from splinter import Browser
from ConfigParser import ConfigParser
import time

cf = ConfigParser()
cf.read(confFile)

b = Browser("chrome")
b.visit(url)


def confcheck():
        conf = self.getConf()
        try:
            conf = {
                "url": self.cf.get("ser", "url"),
                "uname" : self.cf.get("ser", "username"),
                "passwd" : self.cf.get("ser", "password"),
                "tname" : self.cf.get("ser", "project")}

        except Exception as e:
                logging.critical("加载配置文件失败")
                logging.critical(e)
                sys.exit(1)


class base(object):
    def __init__(self):
        self.url = url

    def ClickCSS(t=1, *args):
        for css in args:
            link = b.find_by_css(css)[0]
            link.click()
            time.sleep(t)
            b.screenshot()

    def ClickID(ID, t=1):
        b.click_link_by_id(ID)
        b.screenshot()
        time.sleep(t)

    def ClickDropDown(name):
        css = "tr[data-display=%s] span[class='fa fa-caret-down']" % name
        b.find_by_css(css)[0].click()

    def submit():
        """提交"""
        css = "div[class='modal-footer'] input[type='submit']"
        b.find_by_css(css)[0].click()

    def instance(name, source, flavor, net):
        """创建instance"""

        #跳转到project>instance
        self.projectInstance()

        #点击创建虚拟机
        b.click_link_by_id("instances__action_launch-ng")


        #虚拟机名称
        b.fill("name", name)        

        #选择源
        b.find_by_css("a[href='#']")[3].click()
        b.find_by_css("button[tabindex='0']").click()

        #选择flover
        b.find_by_css("a[href='#']")[4].click()
        b.find_by_css("button[tabindex='0']")[1].click()

        #选择网络
        b.find_by_css("a[href='#']")[5].click()
        b.find_by_css("button[tabindex='0']")[-2].click()

        #点击创建实例
        submit()


    def instanceAction(name, action):
        """操作instance,重启,关闭,热迁移,resize"""

        if action == "resize":
            #点击下拉栏
            css = "tr[data-display=%s] span[class='fa fa-caret-down']" % name

            #选择调整云主机大小
            b.find_by_css("a[class='ajax-modal btn-resize']")[0].click()

            #选择flover
            b.select_by_text("flavor", "m1.tiny")

            #确认
            submit()

            #再次确认
            b.find_by_css("button[value^='instances__confirm']")[0].click()
        elif action == "reboot":
            pass
        elif action == "shutdown":
            pass
        elif action == "liveMigrate":
            self.panelgo(p="admin")

            #点击下拉栏
            ClickDropDown(name)

            #点击云主机热迁移
            b.find_by_css("a[href$='live_migrate']")   
        else:
            alertInfo("暂时不支持此操作 %s" % action)


    def snapshot(name):
        css = "tr[data-display=%s] span[class='fa fa-caret-down']" % name

        #创建快照
        b.fill("name", "snapshot1")

    def snapshotAction(action):
        #删除快照
        if action == "delete":
            b.find_by_css("button[value^='images_delete']")
            b.find_by_css("button[value^='images__delete__']")[0].click()
            b.find_by_css("div[class='modal-footer'] a[href='#']")[1].click()
        else:
            alertInfo("WTF")

    def net(name, subname, cidr):
        """创建网络"""

        #进入项目>网络
        self.panelgo(p="project", location="networks")

        #点击创建网络
        b.click_link_by_id("networks__action_create")

        #编辑网络tab
        b.fill("net_name","net1")

        #编辑子网
        b.fill("subnet_name", "net1-sub")
        b.fill("cidr", "192.168.0.1/24")

        #点击网络详情
        css = "div[class='modal-body'] a[href='#create_network__createsubnetdetailaction']"
        Click(1,css)

        #点击创建网络
        css = "div[class='modal-footer'] button[type='submit']"
        Click(1,css)


    def netExt(name, subname, cidr):
        """创建网络"""

    def netAction(name, action):
        """操作网络,删除"""
        pass

    def route(name):
        """新建路由"""
        pass

    def routeAction(name, action):
        pass

    def secgroup(name):
        pass

    def image(name):
        pass

    def imageAction(name, action):
        pass

    def terminal(stdin):
        pass


class poctest(base):
    def __init__(self):
        self.url = url

    def login(self, uname="admin", passwd="admin"):
        """登陆"""
        b.fill("username", "admin")
        b.fill("password", "admin")
        b.click_link_by_id("loginBtn")

    def panelgo(self, p="project", location="instances", v=9):
        """默认进入侧边栏project>instance"""
        visitURL = "%s/horizon/%s/%s" % (self.url, p, location)
        b.visit(visitURL)

    def alertInfo(info):
        """提示测试内容"""
        b.execute_script("alert(%s)" % info)
        a = b.get_alert()
        sleep(2)
        a.accept()

    def test1(self, restart=True):
        """创建,关闭,重启虚拟机"""

        self.projectInstance()
        
        #点击创建虚拟机
        b.click_link_by_id("instances__action_launch-ng")
        
        #虚拟机名称
        b.fill("name","vm1")        

        #选择源
        b.find_by_css("a[href='#']")[3].click()
        b.find_by_css("button[tabindex='0']").click()

        #选择flover
        b.find_by_css("a[href='#']")[4].click()
        b.find_by_css("button[tabindex='0']")[1].click()
        
        #选择网络
        b.find_by_css("a[href='#']")[5].click()
        b.find_by_css("button[tabindex='0']")[-2].click()

        #点击创建实例
        b.find_by_css("span[ng-bind='::viewModel.btnText.finish']")[0].click()

        #关闭实例

        #重启实例

    def test2(self):
        """创建,删除快照"""
        b.find_by_css("a[id$='snapshot']")[0].click()

        #创建快照
        b.fill("name","snapshot1")
        b.find_by_css("input[type='submit']")[0].click()

        #删除快照
        b.find_by_css("button[value^='images_delete']")
        b.find_by_css("button[value^='images__delete__']")[0].click()
        b.find_by_css("div[class='modal-footer'] a[href='#']")[1].click()        


    def test3(self):
        """调整云主机大小"""

        #选择调整云主机大小
        b.find_by_css("a[class='ajax-modal btn-resize']")[0].click()
        
        #选择flover
        b.select_by_text("flavor","m1.tiny")
        
        #确认
        b.find_by_css("div[class='modal-footer'] input[type='submit']")[0].click()

        #再次确认
        b.find_by_css("button[value^='instances__confirm']")[0].click()


    def test4():
        """虚拟机热迁移"""
        self.projectInstance(p="admin")
        
        #点击下拉栏
        b.find_by_css("tr[class='ajax-update status_up'] span[class='fa fa-caret-down']")[0].click()

        #点击云主机热迁移
        b.find_by_css("a[href$='live_migrate']")        

           
    def test5():
        """创建用户内部私有网络, net1, net2"""
       
        #进入项目>网络
        self.panelgo(p="project", location="networks")

        #点击创建网络
        b.click_link_by_id("networks__action_create")

        #编辑网络tab
        b.fill("net_name","net1")

        #编辑子网
        b.fill("subnet_name", "net1-sub")
        b.fill("cidr", "192.168.0.1/24")

        #点击网络详情
        css = "div[class='modal-body'] a[href='#create_network__createsubnetdetailaction']"
        Click(1,css)

        #点击创建网络
        css = "div[class='modal-footer'] button[type='submit']"
        Click(1,css)
            
        
    def test6():
        """创建用户外部EXT网络"""
        js = "var chk = document.getElementById('id_external');chk.checked = true"

        #跳转admin>networks 
        b.visit()        

        #点击创建网络
        ID = "networks__action_create"
       
        #填入信息
        b.fill("name","pub")
        b.select_by_text("tenant_id","admin")
        b.select("id_network_type","flat")
         

        #选择外部网络
        b.execute_script(js)
       
        #提交
        submit()

           
    def test7():
        """创建路由器"""
        #跳转project>route
        b.visit()

        #点击创建路由
        ID = "routers__action_create"
        b.click_link_by_id()
        
        #填入信息
        b.fill("name", "route1")

        #选择外部网络
        b.select_by_text("external_network")

        #提交
        submit()

        #将新建的子网net1,net2加入此路由器
        #点击刚创建的路由器
        b.find_by_css("tr[data-display='test'] a")[0].click()

        #跳转到接口
        b.click_link_by_href("?tab=router_details__interfaces")
        
        #增加接口
        ID = "interfaces__action_create"

        #填入信息
        css = ""
        ID = [i.value for i in b.find_by_css("select option") if i.text.startswith("net1")][0]
        
        #提交
        submit()
        
           
    def test8():
        """分配及绑定floating ip"""
        #跳转project>instance
        b.visit()

        #点击绑定浮动ip
        

        #获取

        #提交

        #ping

    def test9():
        """不同租户下网络隔离"""
        #跳转

        #登陆terminal

        #执行命令

        #xxx
           
    def test10():
        """安全组访问控制策略"""
       #跳转project>secgroup
 
       #点击新建secgroup

       #配置

       #提交
           
    def test11():
        """创建,挂载云硬盘"""
        #跳转project>volume
        b.visit("http://172.16.0.3/horizon/project/volumes/")

        #点击创建云硬盘
        b.click_link_by_id("volumes__action_create")

        #配置

        #提交
        self.submit()

        #挂载

    def test12():
        """扩展云硬盘"""
        #跳转
        b.visit("http://172.16.0.3/horizon/project/volumes/")

        #点击下拉栏
        css = "tr[data-display='vol11'] span[class='fa fa-caret-down']"

        #点击扩展
        css = "a[id$='action_extend']"
        
        #配置
        b.fill("new_size","2")

        #提交
        submit()
           
    def test13():
        """上传,下载,删除镜像"""
        #跳转
        b.visit("http://172.16.0.3/horizon/project/images/")        

        #点击新建
        ID = "images__action_create"        

        #配置
        b.fill("name","img1")
        alertInfo("请在10秒内选择相应的镜像文件")
        b.select("disk_format","qcow2")       
        while something:
            submit()

        #提交

        #删除
        css = "tr[data-display='img1'] span[class='fa fa-caret-down']"

        css = "tr[data-display='img1'] button[id$='__action_delete']"
        b.find_by_css("div[class='modal-footer'] a")[-1].click()

    def test14():
        """日志数据收集"""
        pass

    def test15():
        """云平台告警"""
        pass

    def test16():
        """openstack服务监控"""
        pass
