# -*- coding: utf-8 -*-
"""
@author: Ye
"""

#==============================================================================
# 用于生成Top IP，Top URL，历史 Top IP，Top URL
#==============================================================================

import pandas as pd
from pandas import DataFrame
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from elasticsearch import Elasticsearch
import arrow

import smtplib
from email.Header import Header 
from email.mime.text import MIMEText 
from email.mime.multipart import MIMEMultipart 
from email.mime.image import MIMEImage

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

##pandas columns width
pd.set_option("display.max_colwidth",200)


##es api
es = Elasticsearch(["http://10.10.99.195:9200/"])

##时间设定
#time_now = arrow.now().format("X") + "000"
index_today = "logstash-" + arrow.now().format("YYYY.MM.DD") 
index_all = "logstash-*"
#time_yesterday = arrow.now().replace(days=-1).format("X")  + "000"
#time_year = arrow.now().replace(years=-1).format("X")  + "000"

##查询字段
#q_url="Request_URL"
#q_ip="X-Forwarded"

q_url="request"
q_ip="remote_addr"

##查询语句设定函数
def top_search(query_str):    
    rets = """{
        "size":0,
        "query":{
            "filtered":{
                "filter":{
                    "bool":{
                        "must":[
                            { "term":{"type":"nginx_access"}}
                        ]
                    }
                },
            "query": {
                "query_string": {
                  "query": "!test.jsp",
                  "analyze_wildcard": true
                }
              }
            }
        },
        "aggs":{
                "%s":{
                    "terms":{"field":"%s",
                    "size":15}
                    }
                }
        }""" %(query_str,query_str + ".raw")

    return rets

#执行查询
today_top_ip = es.search(index=index_today,body=top_search(q_ip))    
today_top_url = es.search(index=index_today,body=top_search(q_url))
year_top_ip = es.search(index=index_all,body=top_search(q_ip))
year_top_url = es.search(index=index_all,body=top_search(q_url))

df_today_ip = DataFrame(today_top_ip["aggregations"][q_ip]["buckets"])
df_today_url = DataFrame(today_top_url["aggregations"][q_url]["buckets"])
df_today_url["name"] = df_today_url.index
df_all_ip = DataFrame(year_top_ip["aggregations"][q_ip]["buckets"])
df_all_url = DataFrame(year_top_url["aggregations"][q_url]["buckets"])
df_all_url["name"] = df_all_url.index

#print df_all_url.head()
#print df_all_ip.head()
#print str(df_today_url["key"])
#print df_today_ip.head()

p1 = sns.factorplot(y="key",x="doc_count",data=df_today_ip,
                    kind="bar",palette="summer")
p1.set_xticklabels(rotation=90)
#p1.set_titles("Today Top 15 IP")
p1.savefig("topip_today.png",dpi=100)

p2 = sns.factorplot(y="doc_count",x="name",data=df_today_url,
                    kind="bar",palette="summer")
p2.set_xticklabels(rotation=30)
#p2.set_titles("Today Top 15 URL")
p2.savefig("topurl_today.png",dpi=100)

p3 = sns.factorplot(y="key",x="doc_count",data=df_all_ip,
                    kind="bar",palette="summer")
p3.set_xticklabels(rotation=90)
#p3.set_titles("Top 15 IP")
p3.savefig("topip_all.png",dpi=100)

p4 = sns.factorplot(y="doc_count",x="name",data=df_all_url,
                    kind="bar",palette="summer")
p4.set_xticklabels(rotation=30)
#p4.set_titles("Top 15 URL")
p4.savefig("topurl_all.png",dpi=100)

msg = MIMEMultipart('alternative') 
msg['Subject'] = Header(u"测试",'utf-8')

text = u"""
<html> 
      <body> 
        <h3>当日IP Top 15</h3>
            <img src="cid:topip_today">            
        <h3>历史IP Top 15</h3>            
            <img src="cid:topip_all"> 
        </p> 
       <h3>当日URL</h3>
""" + df_today_url[["key","name"]].to_html() + """<img src="cid:topurl_today">""" \
+ """<h3>历史URL</h3>""" + df_all_url[["key","name"]].to_html()\
+ """<img src="cid:topurl_all"></html>"""

#print htmls
htmls = MIMEText(text,'html','utf-8')

msg.attach(htmlss)


fp1 = open("topip_today.png","rb")
msgImage1 = MIMEImage(fp1.read())
fp1.close()

msgImage1.add_header('Content-ID','<topip_today>') 
msg.attach(msgImage1)

fp2 = open("topip_all.png","rb")
msgImage2 = MIMEImage(fp2.read())
fp1.close()

msgImage2.add_header('Content-ID','<topip_all>') 
msg.attach(msgImage2)

fp3 = open("topurl_all.png","rb")
msgImage3 = MIMEImage(fp3.read())
fp3.close()

msgImage3.add_header('Content-ID','<topurl_today>') 
msg.attach(msgImage3)

fp4 = open("topurl_all.png","rb")
msgImage4 = MIMEImage(fp4.read())
fp4.close()

msgImage4.add_header('Content-ID','<topurl_all>') 
msg.attach(msgImage4)

sender = 'ops@1ymoney.com' 
receiver = 'dengning@17money.com' 
subject = 'Top IP 测试' 

server = smtplib.SMTP()
#server.set_debuglevel(1)
server.connect("mail.17money.com",'25')
server.starttls()
server.login("nagios@17money.com","jjjr@20151")
server.sendmail(sender,receiver,msg.as_string())
server.quit()
