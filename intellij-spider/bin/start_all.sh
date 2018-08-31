#!/usr/bin/env bash
# crontab -e
# 京东、天猫、淘宝：每周五抓取一次
# 30 0 * * 5 /bin/bash ~/start_all.sh >log.txt 2>&1 &

. ~/.profile
TIME=`date +%y-%m-%d.%H%M`
TODAY=`date +%y-%m-%d`
LOG_DIR=/home/nbot/logs
CACHE_DIR=/home/nbot/cache

# kill old process
ps aux | grep apps. | grep -v grep | awk '{print $2}' | xargs kill -9

cd ~/common-spider/
if [ ! -d ${LOG_DIR} ];then
    mkdir ${LOG_DIR}
fi

nohup ~/.pyenv/versions/3.6.0/bin/python -m apps.jd.app_all true      > ${LOG_DIR}/jd_all_${TIME}".txt" 2>&1 &
sleep 10
nohup ~/.pyenv/versions/3.6.0/bin/python -m apps.tmall.app_all true   > ${LOG_DIR}/tmall_all_${TIME}".txt" 2>&1 &
sleep 10
nohup ~/.pyenv/versions/3.6.0/bin/python -m apps.taobao.app true   > ${LOG_DIR}/taobao_${TIME}".txt" 2>&1 &

# clear old cache files
find ${CACHE_DIR} -type d -name "*.*" | egrep "20[0-9]{2}-[0-9]{2}-[0-9]{2}" | grep -v ${TODAY} | xargs rm -rf
find ${LOG_DIR} -type f -name "*.*" | egrep "20[0-9]{2}-[0-9]{2}-[0-9]{2}.*.txt" | grep -v ${TODAY} | xargs rm -rf


