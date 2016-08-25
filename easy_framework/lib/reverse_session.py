# encoding=utf-8

import gevent.socket
import struct


# 会话管类类，实现子会话、数据首发管理
class ReverseSession(object):
    header_len = 16
    version = 1
    header_flag = b'\xED'
    package_version = b'\x01'
    # 数据包类型
    PKG_REQ = b'\x01'
    PKG_RSP_SUCC = b'\x02'
    PKG_RSP_FAIL = b'\x03'
    PKG_REPORT= b'\x04'

    PKG_HEART = b'\x10'
    PKG_REG = b'\x11'

    PKG_AUTH = b'\xA1'
    PKG_AUTH_SUCC = b'\xA2'
    PKG_AUTH_FAIL = b'\xA3'

    PKG_CLOSE= b'\xFF'

    DEFAULT_BYTES_READ = 8192

    sequnce = 0

    def __init__(self, recvQueue ,sendQueue,sessionId):
        self.recvQueue= recvQueue
        self.sendQueue= sendQueue
        self.sessionId = sessionId
        self.request_sequnce = 0
        self.buffer = ""

    # 接收一个数据包
    def recv(self, max_data_len=10000000,raw = True):
        header,data = self.recvQueue.get()
        #header = struct.unpack('<cccHII3x', all_data[0:self.header_len])
        flag, ver, package_type, seq, total_len,sessionId = header[:6]
        #链接断开标记
        if package_type == '0x10':
            return 1,None

        if sessionId != self.sessionId:
            return -1008,"invalid sessionId"

        # 检查包标记
        if flag != self.header_flag:
            return -1007, "Invalid package"

        # 获取数据长度
        body_len = total_len - self.header_len
        if body_len > max_data_len:
            # 数据包过大
            return -1006, "Body length overflow: " + str(body_len)

        return 0, (header,data)

    def send(self, data,package_type = False):
        if package_type == False:
            package_type = self.PKG_REQ
        return self.__send__(data, package_type)


    def __send__(self, data, package_type, sequnce=0 ):
        # # 生成sequnce, sequnce is not used yet.
        # if sequnce == 0:
        #     self.sequnce += 1
        #     sequnce = self.sequnce

        # 计算包长度
        #body_len = len(data)
        #total_len = body_len + self.header_len

        # 组装包头
        #header = struct.pack("<cccHII3x", self.header_flag, self.package_version, package_type, sequnce, total_len,self.sessionId)


        self.sendQueue.put(((0,0,package_type,0,0,self.sessionId,0,0,0),data))

        return 0, "OK"

    def send_heart(self, data):
        return self.__send__(data, self.PKG_HEART)

    def close(self):
        return self.__send__("", self.PKG_CLOSE)

