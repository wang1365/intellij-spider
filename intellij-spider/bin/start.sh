#!/usr/bin/env bash
# crontab -e
# 30 0 * * * /bin/bash ~/start_all.sh >log.txt 2>&1 &

. ~/.profile
TIME=`date +%Y-%m-%d.%H%M`
TODAY=`date +%y-%m-%d`
LOG_DIR=/home/nbot/logs
CACHE_DIR=/home/nbot/cache

# kill old process
ps aux | grep apps. | grep -v grep | awk '{print $2}' | xargs kill -9

cd ~/common-spider
if [ ! -d ${LOG_DIR} ];then
    mkdir ${LOG_DIR}
fi


nohup ~/.pyenv/versions/3.6.0/bin/python -m apps.jumei.app true >${LOG_DIR}/jumei_$TIME".txt" 2>&1 &
sleep 10
nohup ~/.pyenv/versions/3.6.0/bin/python -m apps.vip.app true   >${LOG_DIR}/vip_$TIME".txt" 2>&1 &

# nohup ~/.pyenv/versions/3.6.0/bin/python -m apps.jd.app true    >${LOG_DIR}/jd_$TIME".txt" 2>&1 &
# nohup ~/.pyenv/versions/3.6.0/bin/python -m apps.tmall.app true >${LOG_DIR}/tmall_$TIME".txt" 2>&1 &


# clear old cache files
find ${CACHE_DIR} -type d -name "*.*" | egrep "20[0-9]{2}-[0-9]{2}-[0-9]{2}" | grep -v ${TODAY} | xargs rm -rf
find ${LOG_DIR} -type f -name "*.*" | egrep "20[0-9]{2}-[0-9]{2}-[0-9]{2}.*.txt" | grep -v ${TODAY} | xargs rm -rf