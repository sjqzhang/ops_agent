#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
import random
from gevent import socket
import struct
import time
import logging
import logging.config
import base64
import os,sys
import json

_curPath = os.path.dirname(os.path.realpath(__file__))
_BasePath = os.path.dirname(os.path.dirname(_curPath))
sys.path.insert(0, _BasePath)

from easy_framework.lib.easy_session import EasySession
from easy_framework.lib.reverse_session import ReverseSession

logger = logging.getLogger("logAgent")


class jsonSession():
    def __init__(self, socket=None,org=None,reverse=False):
        self.version = 1
        if org :
            self.org = org
        else:
            self.org = None
        if reverse == True:
            self.session = socket
        else:
            self.session = EasySession(socket)

    def connect(self, address, unix_socket=False):
        return self.session.connect(address=address,unix_socket=unix_socket)

    def recv(self):
        code,msg = self.session.recv(raw=True)
        if code != 0:
            return code, msg
        header, data_str = msg
        flag, ver, package_type, seq, total_len, sessionId, dataId, org, ip = header[:9]

        if package_type == self.session.PKG_CLOSE:     # authenticate
            return 1100,None
        if package_type == self.session.PKG_REPORT:   # report
            return 0, (header, data_str)
        else:
            return 1106,'package type not support'


    def send(self, data,**kwargs):
        return self.session.send(data,**kwargs)

    def send_report(self,data,version=None):
        if 'org' not in data:
            data['org'] = self.org
        if 'time' not in data:
            data['time'] = time.time()
        data['magic'] = random.randint(0, 100000)
        send_str = json.dumps(data)
        #ret = self.send(send_str,self.session.PKG_REPORT)
        ret = self.send(send_str,
                        package_type=self.session.PKG_REPORT,
                        dataId=data['dataid'],
                        org=data['org'],
                        ip=data['ip'],
                        version=version)

        return ret

    def send_response(self,code,msg,org = None,base64=False):
        resp = {
            'code':code,
            'msg':msg,
            'time':time.time(),
            'magic': 0,
        }
        if org :
            resp['org'] = org
        else:
            resp['org'] = self.org

        send_str = json.dumps(resp)
        return self.send(send_str, package_type=self.session.PKG_RSP_SUCC)


    def close(self):
        logger.info("---------- closing socket ----------")
        self.session.close()


    def ip_to_int(self, ip):
        return struct.unpack('I', struct.pack('I', (socket.ntohl(struct.unpack('I', socket.inet_aton(ip))[0]))))[0]

    def int_to_ip(self, int_ip):
        return socket.inet_ntoa(struct.pack('I', socket.htonl(int_ip)))

    def getLocalIpPort(self):
        return self.session.getsockname()

