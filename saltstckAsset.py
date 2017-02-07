#coding=utf-8

"""
通过saltstatck获取资产清单
"""

import salt.client as sc
from sh import salt
import json


local = sc.LocalClient()
tgt = "*"

grains = local.cmd(tgt,"grains.items")
diskusage = local.cmd(tgt,"disk.usage")

app_name = ["tomcat","zookeeper","redis","fast","mongo","mysql","nginx","web","zabbix","log"]
cols = "Hostname,IP,Memory(GB),CPU Count,OS,/data volum(GB),Project,Application"

ret_file = open("ret.csv","w")
ret_file.write(cols + "\n")

try:
    for i in grains.keys():
        """
        print grains[i]["id"]
        print "ipv4" + ":" ,grains[i]["ipv4"]
        print "mem_total" + ":" , grains[i]["mem_total"] / 1024 + 1
        print "num_cpus" + ":" , grains[i]["num_cpus"]
        print "osfullname" + ":" , grains[i]["osfullname"]
        print "release" + ":" , grains[i]["lsb_distrib_release"]
        """
        if "/data" not in diskusage[i]:
            print "diskusage" + ":" + "have no /data disk"
        else:
            data_vol = int(diskusage[i]["/data"]["1K-blocks"])
            print "diskusage" + ":" , data_vol / 1048576 


        ipv4 = str(grains[i]["ipv4"]).replace(", '127.0.0.1'","")

        hostname = grains[i]["nodename"]
        ipv4 = str(grains[i]["ipv4"]).replace(", '127.0.0.1'","")
        ipv4 = ipv4.replace(",","and")
        mem = grains[i]["mem_total"] / 1024 + 1
        num_cpu = grains[i]["num_cpus"]
        OS = grains[i]["osfullname"] + grains[i]["lsb_distrib_release"]

        if "/data" not in diskusage[i]:
            disk_data = "None"
        else:
            disk_data = data_vol / 1048576

        project = ""

        for j in app_name:
            if j in hostname.lower():
                print hostname.lower()
                app =  j
                break
            else:
                app = "undefined"

        c = ","

        line = hostname + c + ipv4 + c + str(mem) + c + str(num_cpu) + c + str(OS) + c + str(disk_data) + c + project + c + app
        ret_file.write(line + "\n")

except Exception,e:
    print "Exception:\n",e

finally:
    ret_file.close()
