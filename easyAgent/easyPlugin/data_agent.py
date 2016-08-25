#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import traceback
import uuid
import gevent
from gevent.server import StreamServer
from gevent.queue import Queue
import gevent.queue
from gevent.event import Event
import logging
import logging.config
import ConfigParser


from easy_plugin import EasyPlugin
from libs.pbSession import pbSession
from libs.jsonSession import jsonSession
from libs.config import AgentConfig
import libs.server_chooser
import conf.global_vars

_cur_path = os.path.dirname(os.path.abspath(__file__))
_agentBasePath = os.path.dirname(_cur_path)
logging.config.fileConfig(os.path.join(_agentBasePath,"conf","logAgent.conf"))
logger = logging.getLogger("logAgent")

_reportQueue = Queue(10240)

class DataAgent(EasyPlugin):
    def __init__(self, application, name, config):
        EasyPlugin.__init__(self, application, name, config)
        self.conf = AgentConfig()
        self.emitQueue = Queue(10240)
        self.inner_ip = None

    def getLocalIp(self):
        i = 0
        local_ip = None
        # 循环获得local_ip，设置local_ip是在cmd_agent做的，所以这里需要等待
        while i < 3:
            gevent.sleep(3)
            sys_conf = os.path.join(_agentBasePath , "conf","sysconf.ini")
            conf = ConfigParser.ConfigParser()
            conf.optionxform = str
            if os.path.exists(sys_conf):
                conf.read(sys_conf)
            if conf.has_section('sys'):
                local_ip = conf.get('sys','local_ip')
                if local_ip:
                    break
            else:
                # 如果后面换成框架的logger，这里不能直接用logger
                logger.error('not found local_ip, will retry')
            i += 1
        return local_ip

    def handle_customize(self):
        self.generate_uuid()

        # self.inner_ip = self.getLocalIp()
        # if not self.inner_ip:
        #     logger.error('not found local_ip, please restart agent')
        #     sys.exit(1)

        server_groups = self.conf.get('report', 'server_groups')

        job_list = []
        job_list.append(gevent.spawn(self.localReport))
        job_list.append(gevent.spawn(self.localJsonReport))
        jobs = self.send_to_server_groups(server_groups, self.config["linger_ms"], self.config["max_queued_messages"])
        job_list.extend(jobs)

        gevent.joinall(job_list)

    def generate_uuid(self):
        import platform
        if platform.system() == 'Windows':
            uuid_file = "c:\\easyops\\etc\\agentId"
        else:
            uuid_file = "/usr/local/easyops/etc/agentId"

        dir_name = os.path.dirname(uuid_file)

        if not os.path.isdir(dir_name):
            os.makedirs(dir_name)

        if os.path.isfile(uuid_file) and os.path.getsize(uuid_file) > 0:
            return

        with open(uuid_file, 'w+') as f:
            f.write(str(uuid.uuid1()))

    # 处理来自本地json上报的数据
    def processJsonRep(self,socket, address):
        org = self.conf.get('base','client_id')
        jsonSocket = jsonSession(socket=socket,org=org)
        while 1:
            try:
                code, data = jsonSocket.recv()
                if code != 0:
                    logger.error("local receive error (%s %s)"%(code, data))
                    socket.close()
                    break
                try:
                    _reportQueue.put_nowait(data)
                except gevent.queue.Full:
                    logger.error("report queue is full")
                    jsonSocket.send_response(conf.global_vars.ErrCode.QueueFull, 'ok')
                    continue
                jsonSocket.send_response(0, 'ok')
            except Exception, e:
                logger.error("uncaught error, e={}, traceback={}".format(e, traceback.format_exc()))
                socket.close()
                break

    def localJsonReport(self):
        import platform
        if platform.system() == 'Windows':
            rep_port = self.conf.get('report','local_json_port')
            server = StreamServer(('127.0.0.1', rep_port), self.processJsonRep)
            server.serve_forever()
        else:
            from libs.unixSocket import bind_unix_listener
            unix_sock_name = os.path.join(_agentBasePath,'localJsonReport.sock')
            server = StreamServer(bind_unix_listener(unix_sock_name), self.processJsonRep)
            os.chmod(unix_sock_name, 0o777)
            server.serve_forever()

    # 处理来自本地上报的数据
    #@profile
    def processRep(self,socket, address):
        org = self.conf.get('base', 'client_id')
        pbSocket = pbSession(socket=socket,org=org)
        while 1:
            try:
                code, data = pbSocket.recv(decode=False)
                if code != 0:
                    if "connection closed" not in data:
                        logger.error("local receive error (%s %s)"%(code, data))
                    socket.close()
                    break
                try:
                    _reportQueue.put_nowait(data)
                except gevent.queue.Full:
                    logger.error("report queue is full")
                    pbSocket.send_response(conf.global_vars.ErrCode.QueueFull, 'ok')
                    continue
                pbSocket.send_response(0, 'ok')
            except Exception, e:
                logger.error("uncaught error, e={}, traceback={}".format(e, traceback.format_exc()))
                socket.close()
                break

    def localReport(self):
        import platform
        if platform.system() == 'Windows':
            rep_port = self.conf.get('report', 'local_port')
            server = StreamServer(('127.0.0.1', rep_port), self.processRep)
            server.serve_forever()
            pass
        else:

            from libs.unixSocket import bind_unix_listener
            unix_sock_name = os.path.join(_agentBasePath,'localReport.sock')
            server = StreamServer(bind_unix_listener(unix_sock_name), self.processRep)
            os.chmod(unix_sock_name, 0o777)
            server.serve_forever()

    def get_report_server(self, group_name, server_list):
        param_server_list = []
        for server in server_list:
            param_server_list.append("{ip}:{port}".format(ip=server["ip"], port=server["port"]))
        server = libs.server_chooser.ServerChooser.choose_server(param_server_list)
        if server is None:
            logger.error("choose server error, group_name={}, server_list={}".format(group_name, server_list))
            return None
        server_ip, server_port = server.split(":")
        rs = ReportServer(server_ip, server_port)
        logger.info("report server: group_name={}, server={}".format(group_name, server))
        return rs

    #@profile
    def sendToServer(self, group_name, server_list, local_queue, flush_ready_event, linger_ms, max_queued_messages):
        connected = False
        rs = None
        while True:
            try:
                # get msg
                task_msgs = self.batch_fetch(local_queue, flush_ready_event, linger_ms, max_queued_messages)
                if not task_msgs:
                    continue

                # retry 3 times if failed
                while True:
                    # check connection
                    if connected is False:
                        if rs is not None:
                            rs.session.close()
                        rs = self.get_report_server(group_name, server_list)
                        if rs.connect() != 0:
                            gevent.sleep(3)
                            continue
                        else:
                            connected = True

                    # send data
                    ret = rs.batch_send_data(task_msgs)
                    if ret == 0:
                        break

                    logger.error("send msg error!, ret={}".format(ret))
                    connected = False
            except Exception, e:
                connected = False
                logger.error("Uncaught error here! e={}, traceback={}".format(e, traceback.format_exc()))

    #@profile
    def batch_fetch(self, queue, event, linger_ms, max_queued_messages):
        if queue.qsize() < max_queued_messages:
            event.wait(linger_ms / 1000)
        if event.is_set():
            event.clear()
        batch_msgs = [queue.get() for _ in range(queue.qsize())]
        return batch_msgs

    #@profile
    def enqueue(self, queue_event_list, max_queued_messages):
        if len(queue_event_list) == 0:
            return

        while True:
            try:
                # get msg
                task_msg = _reportQueue.get()
                if not task_msg:
                    continue
                dataid, org, ip = task_msg[0][-3:]
                logger.debug('recv msg, org: %s dataid: %s' %(org, dataid))
                # enqueue
                for (q, flush_ready_event) in queue_event_list:
                    if not q.full():
                        q.put_nowait(task_msg)
                    else:
                        logger.error("queue full")
                    if q.qsize() >= max_queued_messages and not flush_ready_event.is_set():
                        flush_ready_event.set()
            except Exception, e:
                logger.error(e)

    def send_to_server_groups(self, server_groups, linger_ms=None, max_queued_messages=None):
        report_queue_list = []
        job_list = []

        for server_group in server_groups:
            report_queue = Queue(10240)
            flush_ready_event = Event()
            report_queue_list.append((report_queue, flush_ready_event))
            job_list.append(gevent.spawn(self.sendToServer, server_group["name"], server_group["hosts"], report_queue, flush_ready_event, linger_ms, max_queued_messages))

        job_list.append(gevent.spawn(self.enqueue, report_queue_list, max_queued_messages))
        return job_list


# 发送本地report到远端服务器
class ReportServer(object):
    """docstring for ReportServer"""
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.session = pbSession()
        #为了兼容旧协议， 先不connect， 发数据之前才connect
        #self.session.connect((server_ip,server_port))

    def connect(self):
        try:
            code, msg = self.session.connect((self.server_ip, self.server_port))
            logger.info("connect to %s:%s => %s %s" %(self.server_ip, self.server_port, code, msg))
            return code
        except Exception, e:
            logger.error(e)
            return 1

    def sendData(self, report_data):
        # send data
        #logger.info(self.easy_sock.socket.getpeername())
        #print report_data
        ret, _ = self.session.send_raw_report(report_data,version = b'\x0E')
        if ret != 0:
            return ret

        # wait response
        ret = 1
        with gevent.Timeout(3, False):
            ret, _ = self.session.recv()

        # result
        return ret

    #@profile
    def batch_send_data(self, msgs):

        data_id_mapped_msgs = {} #data_id => msg
        for header, data_str in msgs:
            flag, ver, package_type, seq, total_len, sessionId, dataId, org, ip = header[:9]
            unique_tuple = (dataId, org, ip)
            if unique_tuple not in data_id_mapped_msgs:
                data_id_mapped_msgs[unique_tuple] = []
            data_id_mapped_msgs[unique_tuple].append(data_str)

        for unique_tuple, batch_msg in data_id_mapped_msgs.iteritems():
            data_id, org, ip = unique_tuple
            ret, msg = self.session.batch_send_report(batch_msg, data_id, org, ip, version=b'\x0E')
            if ret != 0:
                logger.error("batch send report error, ret={}, msg={}".format(ret, msg))
                return ret

            # wait response
            with gevent.Timeout(3, False):
                ret, msg = self.session.recv()
                #print "rsp here, ", ret, len(batch_msg), data_id
                if ret != 0:
                    logger.error("batch send report error, ret={}, msg={}".format(ret, msg))
                    return ret

        # result
        return 0


