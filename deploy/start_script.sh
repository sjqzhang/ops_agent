#!/bin/bash
# Name    : start_script.py
# Date    : 2016.03.28
# Func    : 启动脚本
# Note    : 注意：当前路径为应用部署文件夹

#############################################################
# 用户自定义
app_folder="agent"                 # 项目根目录
process_name="easyAgent collector_agent topo_collector_agent user_log_collector_agent"       # 进程名

install_base="/usr/local/easyops"       # 安装根目录
data_base="/data/easyops"             # 日志/数据根目录

install_path="${install_base}/${app_folder}"
#############################################################
# 通用前置
# ulimit 设定
ulimit -n 100000
export LC_ALL=C
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/easyops/python/dependency

# 非指定安装路径，退出。记得install_path后面不要加/
[[ `pwd` != $install_path ]] && exit 0

# 日志目录
log_path="${install_path}/log"
mkdir -p ${log_path}

# Agent
easy_agent_path="${install_path}/easyAgent"
cd ${easy_agent_path} 
[[ -d log && ! -L log ]] && mv log log.bak
ln -snf ${log_path} log 
../easy_framework/easy_service.py ./conf/easyAgent.yaml start
echo "waiting to init..."
sleep 10


# collector_agent
collector_agent_path="${install_path}/collector_agent"
cd ${collector_agent_path}
[[ -d log && ! -L log ]] && mv log log.bak
ln -snf ${log_path} log
mkdir -p data
# collector
../easy_framework/easy_service.py ./conf/collector.yaml start
# topo_collector
../easy_framework/easy_service.py ./conf/topo_collector.yaml start
# log_collector
[[ ! -d data/user_log_collector/user_log ]] && mkdir -p data/user_log_collector/user_log
[[ ! -d data/user_log_collector/record ]] && mkdir -p data/user_log_collector/record
../easy_framework/easy_service.py ./conf/user_log_collector.yaml start

exit 0



