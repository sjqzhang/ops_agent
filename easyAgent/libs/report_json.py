#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

__author__ = 'linuschen'


import sys
import json
import os
import time
import platform
import ConfigParser
import traceback
#from gevent import socket
import socket


_curPath = os.path.dirname(os.path.abspath(__file__))
_agentBasePath = os.path.dirname(os.path.dirname(_curPath))
sys.path.insert(0, _curPath)
sys.path.insert(0, _agentBasePath)

from easy_framework.lib.easy_session import EasySession
from config import AgentConfig


def get_localip_and_org():
    sys_conf = os.path.join(_agentBasePath ,'easyAgent',"conf","sysconf.ini")
    conf = ConfigParser.ConfigParser()
    conf.optionxform = str
    if os.path.exists(sys_conf):
        conf.read(sys_conf)
    if conf.has_section('sys'):
        local_ip = conf.get('sys','local_ip')
    else :
        print 'Not found local_ip, please retry or restart agent. exit'
        sys.exit(1)

    conf = AgentConfig()
    agent_org = conf.get('base','client_id')
    return local_ip, agent_org

# 获得IP和org
local_ip, agent_org = get_localip_and_org()

e_sock = None


def report(data_id, vals={}, dims={}, ip=None, org=None, retry=1):
    global e_sock, local_ip, agent_org
    ip = ip or local_ip
    org = org or agent_org

    if e_sock is None:
        try:
            if platform.system() == 'Windows':
                e_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                e_sock.connect(("127.0.0.1", 18810))
            else:
                e_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                address = os.path.join(_agentBasePath, 'easyAgent', 'localJsonReport.sock')
                e_sock.connect(address)
        except Exception, e:
            return -1001, 'Connect error: {}'.format(e)

    e_session = EasySession(e_sock)
    
    json_data = {
        'org': org,
        'ip': ip,
        'dataid': data_id,
        'vals': vals,
        'dims': dims
    }
    code, msg = e_session.send(
        json.dumps(json_data),
        package_type=e_session.PKG_REPORT,
        dataId=data_id,
        org=org,
        ip=e_session.ip_to_int(ip),
        version=e_session.package_version_0E
    )
    if code != 0 and not retry:
        e_session.close()
        e_sock = None
        return code, msg

    if code != 0 and retry:
        e_session.close()
        e_sock = None
        return report(data_id=data_id, vals=vals, dims=dims, ip=ip, org=org, retry=0)

    code, msg = e_session.recv()
    if code != 0 and not retry:
        e_session.close()
        e_sock = None
        return code, msg

    if code != 0 and retry:
        e_session.close()
        e_sock = None
        return report(data_id=data_id, vals=vals, dims=dims, ip=ip, org=org, retry=0)

    return 0, "OK"


if __name__ == '__main__':
    data_id = 3410
    vals = {
        "agent_group_id": "5646598b424de3cadfdbcb23",
        "report_type": "heart_beat"
    }
    for i in range(1):
        print report(data_id=data_id, vals=vals)
        time.sleep(1)

