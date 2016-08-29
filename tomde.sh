#!/bin/bash
set -e
###Deploy and Remove the war packages###
###  tomcat1,2,3 server shell script   ###
source /etc/profile
tomcat_dir="/usr/local/tomcatx"

echo the tomcat you selected is tomcat$1
mkdir -p /data/rollback/`date +%F`
today=`date +%F`

case $2 in
        start )
    if [ -z "`ps -ef |grep tomcat$1 |grep -v grep`" ];then
        $tomcat_dir/tomcat$1/bin/startup.sh
    else
    echo "tomcat$1 has started!!!"
    fi
        ;;

        stop )
    ###判断进程是否存在
    if [ ! -z "`ps -ef |grep tomcat$1 |grep -v grep`" ] ;then
            ps -ef |grep tomcat$1 |grep -v grep|awk '{print $2}'|xargs kill -9
            echo "Tomcat$1 killed"
    else
        echo "Tomcat$1 have killed"
    fi
        ;;

        restart )
    ###判断进程是否存在
    if [ ! -z "`ps -ef |grep tomcat$1 |grep -v grep`" ] ;then
            ps -ef |grep tomcat$1 |grep -v grep|awk '{print $2}'|xargs kill -9
            echo "Tomcat killed"
        sleep 2
        $tomcat_dir/tomcat$1/bin/startup.sh
    else
        echo "Tomcat$1 has killed"
        $tomcat_dir/tomcat$1/bin/startup.sh
    fi
        ;;

        rm)
    ###判断进程是否存在
    if [ ! -z "`ps -ef |grep tomcat$1 |grep -v grep`" ] ;then
                ps -ef |grep tomcat$1 |grep -v grep|awk '{print $2}'|xargs kill -9
                echo "Tomcat$1 killed"
        else
                echo "Tomcat$1 have killed"
    fi    
        echo "$tomcat_dir/tomcat$1/webapps/* will be removed"
        rm -fr /data/tomcat$1/webapps/*
        ;;

        mv)
        echo "$tomcat_dir/tomcat$1/webapps/* will be moved"
    ###判断进程是否存在
    if [ ! -z "`ps -ef |grep tomcat$1 |grep -v grep`" ];then
                ps -ef |grep tomcat$1 |grep -v grep|awk '{print $2}'|xargs kill -9
                echo "Tomcat$1 killed"
        else
                echo "Tomcat$1 have killed"
    fi
    ###判断webapps目录里的文件是否存在
    if [ -z $3 ];then
        echo "The war'file is not defined"
        break
    else
        if [ -d $tomcat_dir/tomcat$1/webapps/$3 ];then
            mkdir -p /data/rollback/$today/$3_war
            rm -fr /data/rollback/$today/$3_war/*
            mv  $tomcat_dir/tomcat$1/webapps/$3*  /data/rollback/$today/$3_war/
            echo "moved $tomcat_dir/tomcat$1/webapps/$3  to /data/rollback/$today/$3_war"
        else
            echo "The war package is not exists!!!"
        fi
    fi
        ;;

#        cp)
#        echo "$tomcat_dir/tomcat$1/webapps/* will be moved"
#    ###判断进程是否存在
#    if [ ! -z "`ps -ef |grep tomcat$1 |grep -v grep`" ];then
#                ps -ef |grep tomcat$1 |grep -v grep|awk '{print $2}'|xargs kill -9
#                echo "Tomcat$1 killed"
#        else
#                echo "Tomcat$1 have killed"
#    fi
#    ###判断webapps目录里的文件是否存在
#    counts=`ls /data/tomcat$1/webapps/|wc -w`
#    if [ "$counts" != 0 ];then
#            cp -ar  /data/tomcat$1/webapps/* /data/rollback/$today
#        echo "copy /data/tomcat$1/webapps/* to /data/rollback/$today"
#    else
#        echo "copy Twice!!!!"
#    fi
#        ;;

        back)
    ###判断备份文件夹是否存在已备份文件 
    if [ -z $3 ];then
        echo "The war'filename is not defined"
    else
        echo "$tomcat_dir/tomcat$1/webapps/$3 will be rollback"
        if [ ! -d /data/rollback/$today/$3_war ];then
            echo "The war's filename is not correctlly"
        else
            counts=`ls /data/rollback/$today/$3_war | wc -w`
            if [ "$counts" != 0  ];then
                if [ ! -z "`ps -ef |grep tomcat$1 |grep -v grep`" ];then
                    ps -ef |grep tomcat$1 |grep -v grep|awk '{print $2}'|xargs kill -9
                    echo "Tomcat$1 killed"
                    sleep 2
                else
                    echo "Tomcat$1 have killed"
                fi
                rm -fr $tomcat_dir/tomcat$1/webapps/$3*
                cp -ar /data/rollback/$today/$3_war/$3* $tomcat_dir/tomcat$1/webapps/
                echo "The version back to last time"
                $tomcat_dir/tomcat$1/bin/startup.sh
            else
                echo "The backup directory is empty!!!"
            fi
        fi
    fi
        ;;

        *)
        echo "usage:  tomcat [options] start|stop|restart|rm|mv|back "
        esac
