# encoding=utf-8

import random
import gevent
from gevent.server import StreamServer
from gevent.queue import Queue
from gevent import Timeout
import gevent.socket
import socket
import yaml
import imp
import time
import sys
import os
import logging
import traceback
from cloghandler import ConcurrentRotatingFileHandler
import logging.handlers
from datetime import datetime
import json

from easy_session import EasySession
from easy_daemon import EasyDaemon
from reverse_session import ReverseSession

class EasyApplication (EasyDaemon):
    def __init__(self, conf_file):
        # 配置信息
        self.config = {}
        # 插件对象缓存
        self.plugins = {}
        # 消息转发映射
        self.message_mapping = {}
        # 加载配置
        self.load_config(conf_file)
        # 日志对象
        self.logger = None
        # 协程对象
        self.threads = []
        # 初始化Daemon配置
        daemon_conf = self.config['daemon']
        EasyDaemon.__init__(self, daemon_conf)

    # 加载框架配置
    def load_config(self, conf_file):
        try:
            with open(conf_file, 'r') as f:
                self.config = yaml.load(f)
            # 设置工作目录
            root = self.config['root']
            if not os.path.isabs(root):
                self.config['root'] = os.path.abspath(os.path.dirname(conf_file)+'/'+root)
            os.chdir(self.config['root'])
            # 这种启动方式sys.path并没有加“.”，所以即使切换了工作目录，依旧是无法在工作目录里面import module的
            # 这里要显示将工作目录添加到path
            sys.path.append(self.config['root'])
            print "\033[32mSwitch to working directory:\033[0m ", self.config['root']
        except Exception, e:
            print "Load config failed: ", e
            sys.exit(-1)

    # 加载插件对象
    def load_plugins(self):
        self.logger.info("Load plugins start")
        for info in self.config['plugins']:
            plugin_name = info['name']
            plugin_path = info['path']
            plugin_conf = info['config']
            plugin_class = ''.join(x.capitalize() for x in info['name'].split('_'))

            try:
                sys.path.append(os.path.abspath(plugin_path))
                module = imp.load_module(plugin_class, *imp.find_module(plugin_name, [plugin_path]))
            except Exception, e:
                self.logger.error("Import plugin module failed: %s", traceback.format_exc())
                continue

            try:

                plugin_class = getattr(module, plugin_class)
                plugin = plugin_class(self, plugin_name, plugin_conf)

                # 设置日志对象（加上framework前缀是为了继承框架logger配置）
                plugin.logger = logging.getLogger('framework.' + plugin_name)
                plugin.logger.name = plugin_name

                self.plugins[plugin_name] = plugin
            except Exception, e:
                self.logger.error("Load plugin instance failed: %s", traceback.format_exc())
                continue

            self.logger.info("Load plugins success: %s", plugin_name)

        self.logger.info("Load plugins finish")

        return

    # 注册消息转发规则
    def register_message(self, plugin, message_type):
        # 禁止重复注册
        if self.message_mapping.has_key(message_type):
            return False

        self.message_mapping[message_type] = plugin
        return True

    # 启动应用
    def run(self):
        # 初始化日志对象
        self.init_logger()

        # 加载插件
        self.load_plugins()

        self.threads = []
        for info in self.config['plugins']:
            if info['name'] not in self.plugins:
                continue

            # 初始化插件
            plugin = self.plugins[info['name']]
            code, msg = plugin.plugin_init()
            if code != 0:
                self.logger.error("Init plugin instance failed: %s", msg)
                continue

            self.logger.info("Start plugin: %s", info['name'])

            # 运行插件
            service = info['service']
            if service['type'] == 'network' and service['protocol'] == 'tcp':
                tcp_service = gevent.spawn(self.start_tcp_service, service['ip'], service['port'])
                self.threads.append(tcp_service)
                self.register_message(plugin, service['port'])
                continue

            if service['type'] == 'timer':
                timer_service = gevent.spawn(self.handle_timer, plugin, service['interval'], service.get('start_in_random'))
                self.threads.append(timer_service)
                continue

            if service['type'] == 'ipc' and service['protocol'] == 'unix_socket':
                uds_service = gevent.spawn(self.start_uds_service, service['path'])
                self.threads.append(uds_service)
                self.register_message(plugin, service['path'])
                continue

            if service['type'] == 'customize':
                customize_service = gevent.spawn(plugin.handle_customize)
                self.threads.append(customize_service)

            # 反向连接
            if service['type'] == 'reverse':
                reverse_service = gevent.spawn(self.start_reverse_service, plugin)
                self.threads.append(reverse_service)
                continue

        if len(self.threads) > 0:
            gevent.joinall(self.threads)

        return

    # 启动Tcp服务
    def start_tcp_service(self, ip, port):
        server = StreamServer((ip, port), self.handle_request)
        try:
            server.serve_forever()
        except Exception, e:
            self.logger.error("Start stream server failed: %s", e.__str__())

    # 启动unix domain socket服务
    def start_uds_service(self, path):
        server = StreamServer(self.bind_unix_listener(path), self.handle_uds_request)
        try:
            server.serve_forever()
        except Exception, e:
            self.logger.error("Start stream server failed: %s", e.__str__())

    #反向通道
    def reverse_recv(self,plugin,connection,sendQueue):
        self.connectList[connection]['session'] = {}
        while True:
            try:
                with gevent.Timeout(3 * self.heart_interval):
                    code,data_info= connection.recv(raw=True)
            except Exception,e:
                print e
                break
            except Timeout :
                print "time out"
                self.addrStatus[self.connectList[connection]['addr']]['status'] = 0
                self.clear_gevent_instance(connection)
                break

            if code != 0:
                print "connect error:"+data_info
                self.addrStatus[self.connectList[connection]['addr']]['status'] = 0
                self.clear_gevent_instance(connection)
                break
            header,rawData  = data_info
            flag, ver, package_type, seq, total_len,sessionId = header[:6]
            #收到心跳包,看门狗计数清零
            if package_type == connection.PKG_HEART:
                #print "recv heart package"
                self.connectList[connection]['watchDog'] = 0
                continue

            if (sessionId in self.connectList[connection]['session']):
                sessionQueue = self.connectList[connection]['session'][sessionId]['queue']
                sessionQueue.put((header,rawData))
                if package_type == connection.PKG_CLOSE:
                    del self.connectList[connection]['session'][sessionId]
            else:
                sessionQueue = Queue()
                self.connectList[connection]['session'][sessionId] = {}
                self.connectList[connection]['session'][sessionId]['queue'] = sessionQueue
                r_session = ReverseSession(sessionQueue,sendQueue,sessionId)
                plugin_instance = gevent.spawn(plugin.handle_request,r_session)
                self.connectList[connection]['session'][sessionId]['instance'] = plugin_instance
                sessionQueue.put((header,rawData))

    def clear_gevent_instance(self,connection):
        print "clear gevent instance"
        if connection in self.connectList:
            sessionList = self.connectList[connection]['session']
            #清理插件协程
            for sessionId in sessionList:
                gevent.kill(sessionList[sessionId]['instance'])
            #清理发送协程
            sendInstance = self.connectList[connection]['sendInstance']
            recvInstance = self.connectList[connection]['recvInstance']
            connection.close()
            del self.connectList[connection]
            gevent.kill(sendInstance)
            gevent.kill(recvInstance)



    def reverse_send(self,connection,sendQueue):
        while True:
            header_info,sendData = sendQueue.get()

            #import struct
            #header = struct.unpack('<cccHII3x', sendData[0:16])
            #package_type,sessionId,dataId = header_info[:6]
            flag, ver, package_type, seq, total_len,sessionId = header_info[:6]
            if sessionId in self.connectList[connection]['session']:
                if package_type == connection.PKG_CLOSE:
                    del self.connectList[connection]['session'][sessionId]
                #code,msg = connection.send_raw(sendData)
                code,msg = connection.send(sendData,package_type=package_type,sessionId = sessionId)
                if code != 0:
                    self.clear_gevent_instance(connection)
                    break
            elif package_type == connection.PKG_HEART:
                #code,msg = connection.send_raw(sendData)
                code,msg = connection.send(sendData,package_type=package_type,sessionId = sessionId)


    # 建立反向连接服务
    def start_reverse_service(self, plugin):
        # 建立反向连接
        self.connectList = {}
        self.heart_interval = 10
        self.addrStatus = {}
        addrList = plugin.getServerList()
        while True:
            for addr in addrList:
                ip = addr['ip']
                port = addr['port']
                addr_str = "%s:%s"%(ip,port)
                # 已连接，且心跳正常,则跳过
                if (addr_str in self.addrStatus) and (self.addrStatus[addr_str]['status'] == 0):
                    continue

                self.logger.info("connect to %s" %addr_str)
                self.addrStatus[addr_str] = {}
                self.addrStatus[addr_str]['addr'] = addr
                sendQueue = Queue()
                #建立连接
                connection = EasySession()

                self.addrStatus[addr_str]['connection'] =connection
                self.connectList[connection] = {}
                self.connectList[connection]['addr'] = addr_str
                self.connectList[connection]['watchDog'] = 0

                code, msg = connection.connect((ip, port))
                if code != 0:
                    self.addrStatus[addr_str]['status'] = 1
                    connection.close()
                    self.logger.error("connect server error, ip:%s, port:%s, msg:%s" %(ip, port, msg))
                    continue

                self.addrStatus[addr_str]['status'] = 0
                #register
                #agentId = plugin.getAgentId(connection)
                #msg={
                #    "agentId":agentId
                #}
                msg = plugin.getRegisterInfo(connection)
                code,msg = connection.send_reg(json.dumps(msg))
                if code != 0:
                    connection.close()
                    self.logger.error("register error, msg:%s" %msg)
                    break
                recv = gevent.spawn(self.reverse_recv,plugin,connection,sendQueue)
                send = gevent.spawn(self.reverse_send,connection,sendQueue)
                self.connectList[connection]['sendInstance'] = send
                self.connectList[connection]['recvInstance'] = recv
                r_session = ReverseSession(None,sendQueue,0)
                self.addrStatus[addr_str]['r_session'] = r_session

            count = 0
            errList = []
            while True:
                count += 1
                gevent.sleep(self.heart_interval)
                for addr_str in self.addrStatus:
                    if 'r_session' not in self.addrStatus[addr_str] \
                        or 'connection' not in self.addrStatus[addr_str] \
                        or 'status' not in self.addrStatus[addr_str]:
                        errList.append(addr_str)
                        continue

                    if self.addrStatus[addr_str]['status'] != 0:
                        errList.append(addr_str)
                        continue
                    #发送心跳包
                    msg = {
                        "ts": int(time.time()),
                        "tz": int(round((datetime.now() - datetime.utcnow()).total_seconds()))
                    }
                    self.addrStatus[addr_str]['r_session'].send_heart(json.dumps(msg))
                    connection = self.addrStatus[addr_str]['connection']
                    if (connection not in self.connectList) or (self.connectList[connection]['watchDog'] > 3* self.heart_interval):
                        errList.append(addr_str)
                        self.addrStatus[addr_str]['status'] = 1
                if len(errList) > 0:
                    break
            gevent.sleep(3)

    # 处理网络请求
    def handle_request(self, socket, address):
        ip, port = socket.getsockname()

        plugin = self.message_mapping.get(port)
        if plugin:
            session = EasySession(socket)
            plugin.handle_request(session)
            session.close()

    # 处理unix_socket请求
    def handle_uds_request(self, socket, address):
        name = socket.getsockname()

        plugin = self.message_mapping.get(name)
        if plugin:
            session = EasySession(socket)
            plugin.handle_request(session)
            session.close()

    # 处理定时事件
    def handle_timer(self, plugin, interval, start_in_random=False):
        #后台定时任务，在启动前都随机延时，分散定时任务
        if start_in_random:
            gevent.sleep(random.randint(1, interval))
        while True:
            # 计算任务处理时间，要扣除相应等待时间

            t1 = time.time()
            try:
                plugin.handle_timer()
            except SystemExit,e:
                raise e
            except:
                self.logger.error(traceback.format_exc())
            t2 = time.time()

            t = t2 - t1
            if t <= interval:
                # 睡眠要扣除任务执行时间
                gevent.sleep(interval - t)
            else:
                # 任务执行超过定时间隔，交出控制权
                gevent.sleep()

    # 创建新session
    def create_session(self):
        return EasySession()

    # 获取插件对象
    def get_plugin(self, name):
        if name in self.plugins:
            return 0, self.plugins[name]
        else:
            return -1, None

    # 初始化日志对象
    def init_logger(self):
        if 'log' not in self.config:
            return

        if self.logger is None:
            self.logger = logging.getLogger('framework')

        conf = self.config['log']
        max_size = conf['max_size']
        max_backup = conf['max_backup']
        level = conf['level']
        log_format = conf['format']

        formatter = logging.Formatter(log_format)

        logfile = os.path.abspath(conf['file'])
        logfolder = os.path.dirname(logfile)
        if not os.path.exists(logfolder):
            os.makedirs(logfolder, 0o755)
        rotate_handler = logging.handlers.RotatingFileHandler(logfile, "a", max_size, max_backup)
        rotate_handler.setFormatter(formatter)
        self.logger.addHandler(rotate_handler)
        if level.lower() == 'debug' and os.environ.get('EASY_DEBUG') == '1':
            self.logger.addHandler(logging.StreamHandler())

        level_mapping = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'error': logging.ERROR
        }
        if level in level_mapping:
            self.logger.setLevel(level_mapping[level])
        else:
            self.logger.setLevel(logging.INFO)

    def unlink(self, path):
        from errno import ENOENT
        try:
            os.unlink(path)
        except OSError, ex:
            if ex.errno != ENOENT:
                raise

    def bind_unix_listener(self, path, backlog=50, user=None):
        try:
            sock = gevent.socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.setblocking(0)
            self.unlink(path)
            sock.bind(path)
            if user is not None:
                import pwd
                user = pwd.getpwnam(user)
                os.chown(path, user.pw_uid, user.pw_gid)
            os.chmod(path, 0777)
            sock.listen(backlog)
        except Exception, e:
            self.logger.error("Create unix socket failed: %s", e.__str__())
            return None
        return sock
