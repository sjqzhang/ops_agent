# encoding=utf-8

import gevent.socket
import socket
import struct


# 会话管类类，实现子会话、数据首发管理
class EasySession(object):
    header_len = 16
    header_len_0E = 32
    version = 1
    header_flag = b'\xED'
    package_version = b'\x01'
    package_version_0E = b'\x0E'
    # 数据包类型
    PKG_REQ = b'\x01'
    PKG_RSP_SUCC = b'\x02'
    PKG_RSP_FAIL = b'\x03'
    PKG_REPORT = b'\x04'
    PKG_BATCH_REPORT = b'\x05'

    PKG_HEART = b'\x10'
    PKG_REG = b'\x11'

    PKG_AUTH = b'\xA1'
    PKG_AUTH_SUCC = b'\xA2'
    PKG_AUTH_FAIL = b'\xA3'

    PKG_CLOSE= b'\xFF'

    DEFAULT_BYTES_READ = 8192

    sequnce = 0
    cur_package_version = None

    def __init__(self, p_socket=None):
        self.socket = p_socket
        if self.socket is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.request_sequnce = 0
        self.buffer = ""

    def connect(self, address, unix_socket=False):
        if unix_socket is True:
            self.socket = gevent.socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            self.socket = gevent.socket.socket()

        try:
            self.socket.connect(address)
        except Exception, e:
            return -1010, "Connect failed: " + str(e)

        return 0, "OK"

    # 接收一个数据包
    def recv(self, max_data_len=10000000,raw=False):
        # 接收包头
        code, data = self.__recv_all__(self.header_len)
        if code != 0:
            return code, data

        """
        协议头说明：
        #版本0x01
        #总长度16字节
        1 标记位，1字节，0xED
        2 版本号，1字节，0x01
        3 数据包类型，1字节，类型值如下
            0x01 普通请求
            0x02 成功返回
            0x03 失败返回
            0xa1 访问鉴权
            0xa2 鉴权成功
            0xa3 鉴权失败
        4 序列号，2字节，Request随机生成，Response返回对应序列号
        5 数据包长度，4字节
        5 sessionId，4字节
        6 扩展字段，3字节

        #版本0x0E
        #总长度32字节
        1 标记位，1字节，0xED
        2 版本号，1字节，0x0E
        3 数据包类型，1字节，类型值如下
            0x01 普通请求
            0x02 成功返回
            0x03 失败返回
            0xa1 访问鉴权
            0xa2 鉴权成功
            0xa3 鉴权失败
        4 序列号，2字节，Request随机生成，Response返回对应序列号
        5 数据包长度，4字节
        6 sessionId，4字节
        7 dataId，4字节
        8 org，4字节
        9 ip，4字节
        10 扩展字段，7字节
        """
        header_data = data
        header = struct.unpack('<cccHII3x', data)
        flag, ver, package_type, seq, total_len,sessionId = header

        # 检查包标记
        if flag != self.header_flag:
            return -1007, "Invalid package"
        if ver == self.package_version_0E:
            self.cur_package_version= self.package_version_0E
            # 新版本协议32字节,继续接收包头
            code, data_2 = self.__recv_all__(self.header_len_0E - self.header_len)
            if code != 0:
                return code, data
            header_data = data + data_2
            header = struct.unpack('<cccHIIIII7x', header_data)
            flag, ver, package_type, seq, total_len, sessionId, dataId,org,ip = header
            # 获取数据长度
            body_len = total_len - self.header_len_0E
        else:
            self.cur_package_version= self.package_version
            # 获取数据长度
            body_len = total_len - self.header_len



        if body_len > max_data_len:
            # 数据包过大
            return -1006, "Body length overflow: " + str(body_len)

        # 接收包体
        code, data = self.__recv_all__(body_len)
        if code != 0:
            return code, data

        # 存储请求序列号
        self.request_sequnce = seq

        if raw == True:
            return 0,(header,data)
        return 0, data

    def __recv_all__(self, length):
        if not self.connected():
            return -1004, "Not connected"
        try:
            if length <= len(self.buffer):
                ret_buf = self.buffer[:length]
                self.buffer = self.buffer[length:]
                return 0, ret_buf

            to_recv = length - len(self.buffer)
            if to_recv < self.DEFAULT_BYTES_READ:
                recv_bytes = self.DEFAULT_BYTES_READ
            else:
                recv_bytes = to_recv

            recv_size = len(self.buffer)
            if recv_size > 0:
                buffers = [self.buffer]
            else:
                buffers = []

            while to_recv > 0:
                buff = self.socket.recv(recv_bytes)
                if buff:
                    to_recv -= len(buff)
                    buffers.append(buff)
                    recv_size += len(buff)
                else:
                    break

            if length == recv_size:
                self.buffer = ""
                return 0, "".join(buffers)

            if length < recv_size:
                diff = len(buffers[len(buffers) - 1]) - (recv_size - length)
                self.buffer = buffers[len(buffers) - 1][diff:]
                return 0, "".join(buffers[:len(buffers) - 1]) + buffers[len(buffers) - 1][:diff]

        except Exception, e:
            self.socket.close()
            code = -1004
            msg = "Receive bytes failed: " + str(e)
            self.close()
            return code, msg

        if to_recv > 0:
            self.close()
            return -1004, "connection closed"

        return 0, ""

    def __send__(self, data, package_type, **kwargs):
        # # 生成sequnce, sequnce is not used yet.
        # if sequnce == 0:
        #     self.sequnce += 1
        #     sequnce = self.sequnce

        sequnce = kwargs.get('sequnce',0)
        sessionId = kwargs.get('sessionId',0)
        dataId = kwargs.get('dataId',0)
        org = kwargs.get('org',0)
        ip = kwargs.get('ip',0)

        #判断版本号
        version = kwargs.get('version',0)
        if version :
            package_version = version
        elif self.cur_package_version:
            package_version = self.cur_package_version
        else:
            package_version = b'\x01'


        # 计算包长度
        body_len = len(data)
        if package_version == self.package_version_0E:
            total_len = body_len + self.header_len_0E

            # 组装包头
            header = struct.pack("<cccHIIIII7x",
                                 self.header_flag,
                                 package_version,
                                 package_type,
                                 sequnce,
                                 total_len,
                                 sessionId,
                                 dataId,
                                 org,
                                 ip
                                 )
        elif package_version == self.package_version:
            total_len = body_len + self.header_len

            # 组装包头
            header = struct.pack("<cccHII3x", self.header_flag, package_version, package_type, sequnce, total_len,sessionId)

        # 发送包头
        code, msg = self.__send_all__(header)
        if code != 0:
            return code, msg

        # 发送包体
        code, msg = self.__send_all__(data)
        if code != 0:
            return code, msg

        return 0, "OK"

    def __send_all__(self, data):
        if not self.connected():
            return -1005, "Not connected"
        try:
            to_send = len(data)
            send_view = memoryview(data)
            while to_send > 0:
                nbytes = self.socket.send(send_view)
                if nbytes:
                    to_send -= nbytes
                    send_view = send_view[nbytes:]
                else:
                    break
        except Exception, e:
            code = -1005
            msg = "Send error: " + str(e)
            self.close()
            return code, msg

        if to_send > 0:
            self.close()
            return -1005, "Connection closed"

        return 0, 'OK'

    def send_request(self, data):
        return self.__send__(data, self.PKG_REQ)

    def send(self, data,**kwargs):
        package_type = kwargs.pop('package_type',self.PKG_REQ)

        ret = self.__send__(data,package_type, **kwargs )
        return ret

    def send_raw(self, data):
        return self.__send_all__(data)

    def send_response(self, data, rsp_type):
        return self.__send__(data, rsp_type, sequnce=self.request_sequnce)

    def send_reg(self, data):
        return self.__send__(data, self.PKG_REG)

    def send_heart(self, data):
        return self.__send__(data, self.PKG_HEART)

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def get_my_ip(self):
        if self.socket is None:
            return None
        return self.socket.getsockname()[0]
    def ip_to_int(self, ip):
        return struct.unpack('I', struct.pack('I', (socket.ntohl(struct.unpack('I', socket.inet_aton(ip))[0]))))[0]

    def int_to_ip(self, int_ip):
        return socket.inet_ntoa(struct.pack('I', socket.htonl(int_ip)))
    def connected(self):
        return self.socket is not None
