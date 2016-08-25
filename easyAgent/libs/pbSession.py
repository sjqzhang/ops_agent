import random
from gevent import socket
import struct
import time
import logging
import logging.config
import base64
import os,sys
import chardet
import platform
if platform.system() == 'Windows':
    import easyPb_pb2 as pb
else:
    import easyPb_proto as pb


_curPath = os.path.dirname(os.path.realpath(__file__))
_BasePath = os.path.dirname(os.path.dirname(_curPath))
sys.path.insert(0, _BasePath)

from easy_framework.lib.easy_session import EasySession
from easy_framework.lib.reverse_session import ReverseSession

logger = logging.getLogger("logAgent")


class pbSession():
    def __init__(self, socket=None, org=None, reverse=False):
        self.version = 1
        if org :
            self.org = org
        else:
            self.org = None
        if reverse is True:
            self.session = socket
        else:
            self.session = EasySession(socket)
            self.package_version = self.session.package_version
            self.package_version_0E = self.session.package_version_0E

    def connect(self, address, unix_socket=False):
        return self.session.connect(address=address,unix_socket=unix_socket)

    def recv(self, decode=True):
        code, msg = self.session.recv(raw=True)
        if code != 0:
            return code, msg
        if decode is False:
            return code, msg
        header, data_str = msg
        flag, ver, package_type, seq, total_len, sessionId = header[:6]
        if total_len == len(data_str):
            data_str = data_str[self.session.header_len:]

        if package_type == self.session.PKG_CLOSE:     # authenticate
            return 1100,None
        if package_type == self.session.PKG_AUTH:     # authenticate
            self.authenticate()
            return 0, {"op": "auth", "version": ver, "data": ""}
        elif package_type == self.session.PKG_REQ:   # request
            req = pb.request()
            req.ParseFromString(data_str)
            return 0, {"op": "request", "version": ver, "data": req}
        elif package_type == self.session.PKG_RSP_SUCC or package_type == self.session.PKG_RSP_FAIL:   # response
            resp = pb.response()
            resp.ParseFromString(data_str)
            return 0, {"op": "response", "version": ver, "data": resp}
        elif package_type == self.session.PKG_REPORT:   # report
            rep = pb.report()
            rep.ParseFromString(data_str)
            return 0, {"op": "report", "version": ver, "data": rep}

    def send(self, data, **kwargs):
        return self.session.send(data,**kwargs)

    def send_report(self, data, version=None):
        if data.org == 0 or data.org is None:
            data.org = self.org
        if not data.time:
            data.time = time.time()
        if not data.magic:
            data.magic = random.randint(0, 100000)
        send_str = data.SerializeToString()
        send_str = str(send_str)
        ret = self.send(send_str, package_type=self.session.PKG_REPORT, dataId=data.dataid, org=data.org, ip=data.ip, version=version)
        return ret

    # param data :(header,pbStr)
    def send_raw_report(self, data, version=None):
        header, pbStr = data
        flag, ver, package_type, seq, total_len, sessionId, dataId, org, ip = header[:9]
        ret = self.send(pbStr, package_type=self.session.PKG_REPORT, dataId=dataId, org=org, ip=ip, version=version)
        return ret

    # param data :(header,pbStr)
    def batch_send_report(self, batch_msg, data_id, org, ip, version=None):
        pb_msg = pb.batch_report()
        for msg in batch_msg:
            pb_msg.msg.append(bytes(msg))
        converted = pb_msg.SerializeToString()
        converted = str(converted)
        ret = self.send(converted, package_type=self.session.PKG_BATCH_REPORT, dataId=data_id, org=org, ip=ip, version=version)
        return ret

    def send_response(self,code,msg,org = None,base64=False):
        resp = pb.response()
        resp.code = code
        if org :
            resp.org = org
        else:
            resp.org = self.org

        if type(msg) != unicode:
            ret = chardet.detect(msg)
            charset = ret['encoding']
            if charset is not None and charset != 'ascii':
                msg = msg.decode(charset)
        resp.msg = msg
        resp.time = time.time()
        resp.magic = random.randint(0, 100000)
        send_str = resp.SerializeToString()
        send_str = str(send_str)
        ret = self.send(send_str,package_type = self.session.PKG_RSP_SUCC)
        return ret

    def close(self):
        logger.info("---------- closing socket ----------")
        self.session.close()


    def ip_to_int(self, ip):
        return struct.unpack('I', struct.pack('I', (socket.ntohl(struct.unpack('I', socket.inet_aton(ip))[0]))))[0]

    def int_to_ip(self, int_ip):
        return socket.inet_ntoa(struct.pack('I', socket.htonl(int_ip)))

    def getLocalIpPort(self):
        return self.session.getsockname()

