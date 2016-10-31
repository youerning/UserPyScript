# -*- coding: utf-8 -*-
"""
Created on Sat Dec 05 18:15:33 2015
 
@author: Administrator
"""
 
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 04 00:35:24 2015
 
@author: Ye
"""
 
from splinter.browser import Browser
from time import sleep
 
#用户名，密码
username = "用户名"
passwd = "密码"
#cookies值得自己去找,下面两个分别是上海，长沙,怎么找blog中说明了
starts = "%u4E0A%u6D77%2CSHH"
ends = "%u6C38%u5DDE%2CAOQ"
#ends = "%u957F%u6C99%2CCSQ"
#时间格式2016-01-31
dtime = "2016-02-02"
#车次，选择第几趟，0则从上之下依次点击
order = 0
###乘客名
pa = u"乘客名(常用联系人)"
###车次类型
ttype="GC-高铁/城际"
 
#网址
ticket_url = "https://kyfw.12306.cn/otn/leftTicket/init"
login_url = "https://kyfw.12306.cn/otn/login/init"
initmy_url = "https://kyfw.12306.cn/otn/index/initMy12306"
config_url = "https://kyfw.12306.cn/otn/confirmPassenger/initDc"
 
def login():
    b.find_by_text(u"登录").click()
    sleep(3)
    b.fill("loginUserDTO.user_name",username)
    sleep(1)
    b.fill("userDTO.password",passwd)
    sleep(1)
    b.execute_script('alert("自行输入验证码吧~")')
    print u"等待验证码，自行输入..."
    sleep(10)
         
def huoche():
    global b
    b = Browser(driver_name="chrome")
    b.visit(ticket_url)
    b.execute_script('alert("开始刷票喽~~~~")')
    sleep(2)
    b.get_alert().dismiss()
     
    while b.is_text_present(u"登录"):
        sleep(1)
        login()
        if b.url == initmy_url:
            break
       
    try:
        #跳回购票页面
        b.visit(ticket_url)
         
        #加载查询信息
        b.cookies.add({"_jc_save_fromStation":starts})
        b.cookies.add({"_jc_save_toStation":ends})
        b.cookies.add({"_jc_save_fromDate":dtime})
        b.reload()
        i = 1       
         
        #循环点击预订
        if order != 0:
            while b.url == ticket_url:
                b.find_by_text(u"查询").click()
#                b.find_by_text(ttype).click()
                 
                if b.find_by_text(u"预订"):
                    sleep(0.3)
                    b.find_by_text(u"预订")[order - 1].click()
                    print b.url
                     
                    if b.is_text_present(u"证件号码",wait_time=0.2):
#                        print [ i.text for i in b.find_by_text(pa) ]
                        b.find_by_text(pa)[1].click()
                         
                else:
                    b.execute_script('alert("似乎没有可预订选项")')
                    b.get_alert().dismiss()
                    pass
                  
        else:
            while b.url == ticket_url:
                b.find_by_text(u"查询").click()
                if b.find_by_text(u"预订"):
                    sleep(0.3)
                    for i in b.find_by_text(u"预订"):                 
                        i.click()
                        sleep(0.1)
                        if b.is_text_present(u"证件号码"):
                            b.find_by_text(pa)[1].click()
                                                         
                    else:
                        b.execute_script('alert("似乎没有可预订选项")')
                        b.get_alert().dismiss()
                        pass
                      
        b.execute_script('alert("能做的都做了")')
        b.get_alert().dismiss()
         
        print  u"能做的都做了.....不再对浏览器进行任何操作"
         
    except Exception:
        print u"出错了...."
         
if __name__ == "__main__":
    huoche()
