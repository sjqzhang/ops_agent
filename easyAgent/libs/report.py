#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

__author__ = 'linus'

import sys
import json
import os
import time
import platform
import ConfigParser
#from gevent import socket
import socket

_curPath = os.path.dirname(os.path.abspath(__file__))
_agentBasePath = os.path.dirname(os.path.dirname(_curPath))
sys.path.insert(0, _curPath)
sys.path.insert(0, _agentBasePath)

#import easyPbV2 as pb2
if platform.system() == 'Windows':
    from easyAgent.libs import easyPb_pb2 as pb2
else:
    import easyPb_proto as pb2
from pbSession import pbSession

sys_conf = os.path.join(_agentBasePath ,'easyAgent',"conf","sysconf.ini")
conf = ConfigParser.ConfigParser()
conf.optionxform = str
if os.path.exists(sys_conf):
    conf.read(sys_conf)
if conf.has_section('sys'):
    local_ip = conf.get('sys','local_ip')
else :
    local_ip = '0.0.0.0'

from config import AgentConfig

conf = AgentConfig()
agent_org = conf.get('base','client_id')

pb_sock = None

def connect():
    global pb_sock
    if pb_sock is not None:
        return pb_sock

    try:
        if platform.system() == 'Windows':
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1",18810))
        else:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            address = os.path.join(_agentBasePath, 'easyAgent','localReport.sock')
            s.connect(address)
    except Exception, e:
        print e
        return None
    return pbSession(socket=s, org=agent_org)


def close_pb_sock():
    global pb_sock
    pb_sock.close()
    pb_sock = None


def report(data_id, dims={}, vals={}, org=False):
    """
    data_id: 7001
    dims: {'test_case_id': 123}
    vals: {70011001: 'aaaa'} 或 [{70011001: 'aaaa'}]，支持一次性上报多条
    """
    global pb_sock
    if not org:
        org = agent_org
    pb_sock = connect()
    if pb_sock is None:
        return -1001, "Connect error"
    pb_sock.org = org
    def _add_key(field, v):
        if isinstance(v, (str, unicode)):
            field.str_key = v 
        else:
            field.int_key = v
    def _add_val(field, v):
        if isinstance(v, (str, unicode)):
            field.str_val = v 
        elif isinstance(v, (dict,list,tuple)):
            field.str_val = json.dumps(v)
        elif isinstance(v, (float,)):
            field.int_val = int(v)
        elif isinstance(v, (int, long)):
            field.int_val = v
        else:
            raise ValueError('pb report did not support %s, type is %s' %(v, type(v)))

    if isinstance(vals, dict):
        vals_list = [vals]
    else:
        vals_list = vals

    for vals in vals_list:
        if not vals:
            continue
        cnt = 0
        while True:
            cnt += 1
            rep=pb2.report()
            rep.ip=pb_sock.ip_to_int(local_ip)
            rep.time=time.time()
            rep.dataid = data_id
            rep.type=2
            for k,v in dims.iteritems():
                if v is None:
                    continue
                field=rep.dims.add()
                _add_key(field, k)
                _add_val(field, v)
            for k,v in vals.iteritems():
                if v is None:
                   continue
                field=rep.vals.add()
                _add_key(field, k)
                _add_val(field, v)
            code, msg = pb_sock.send_report(rep,pb_sock.package_version_0E)
            if code != 0:
                close_pb_sock()
                pb_sock = connect()
                if pb_sock is None:
                    return -1001, 'Connect error'
                if cnt == 2:
                    return code, msg
                continue

            code, msg = pb_sock.recv()
            if code == 0:
                break
            else:
                close_pb_sock()
                pb_sock = connect()
                if pb_sock is None:
                    return -1001, 'Connect error'

            if cnt == 2:
                return code, msg
    return 0, 'OK'


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'Usage: ./report data_id msg'
        sys.exit(1)
    else:
        data_id = sys.argv[1]
        vals = {'test': sys.argv[2]}
        print report(int(data_id), vals=vals)


