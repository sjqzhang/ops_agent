#!/bin/bash
# Name    : stop_script.py
# Date    : 2016.03.28
# Func    : 停止脚本
# Note    : 注意：当前路径为应用部署文件夹

#############################################################
# 用户自定义
app_folder="agent"                 # 项目根目录
process_name="easyAgent collector_agent topo_collector_agent user_log_collector_agent"       # 进程名

install_base="/usr/local/easyops"       # 安装根目录
data_base="/data/easyops"             # 日志/数据根目录

install_path="${install_base}/${app_folder}"
#############################################################

# 非指定安装路径，退出。记得install_path后面不要加/
[[ `pwd` != $install_path ]] && exit 0

# easyAgent
cd ${install_path}/easyAgent
../easy_framework/easy_service.py ./conf/easyAgent.yaml stop

# collector_agent
cd ${install_path}/collector_agent
# collector
../easy_framework/easy_service.py ./conf/collector.yaml stop
# jstatus
ps -fC java |grep jstatus | grep -v 'grep' | awk '{print $2}' |xargs kill -9 > /dev/null 2>&1
# topo_collector
../easy_framework/easy_service.py ./conf/topo_collector.yaml stop
# user_log_collector
../easy_framework/easy_service.py ./conf/user_log_collector.yaml stop

if [[ ${process_name}x != x ]]; then
    for pname in ${process_name}; do
        ps -C ${pname} -o command,pid | grep ${pname} | awk '{print $2}' | xargs kill -9 > /dev/null 2>&1
    done
fi

exit 0
