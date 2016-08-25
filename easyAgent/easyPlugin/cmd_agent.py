#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import gevent
from easy_plugin import EasyPlugin
#from pkg.script.common import runShell
import random

from libs.pbSession import pbSession
import logging
import logging.config
import os
from libs.config import AgentConfig
import ConfigParser

_agentBasePath = os.path.abspath(os.path.curdir)
logging.config.fileConfig(os.path.join(_agentBasePath,"conf","logAgent.conf"))
logger = logging.getLogger("logAgent")


class CmdAgent(EasyPlugin):
    def __init__(self, application, name, config):
        self.startTime = time.time()
        EasyPlugin.__init__(self, application, name, config)

    def getAgentId(self,conn):
        conf = AgentConfig()
        org = conf.get('base','client_id')
        inner_ip = conn.get_my_ip()
        self.inner_ip = inner_ip
        self.setLocalIp(self.inner_ip)
        agentId = "%s_%s"%(org,inner_ip)
        return agentId
    def getRegisterInfo(self,conn):
        conf = AgentConfig()
        org = conf.get('base','client_id')
        version = conf.get('base','version')
        inner_ip = conn.get_my_ip()
        self.inner_ip = inner_ip
        self.setLocalIp(self.inner_ip)
        agentId = "%s_%s"%(org,inner_ip)
        msg={
            "agentId":agentId,
            "org":org,
            "version":version,
            "startTime":int(self.startTime),
        }
        return msg

    def getServerList(self):
        conf = AgentConfig()
        serverList = conf.get('command','servers')
        return serverList
    def setLocalIp(self,ip):
        sys_conf = os.path.join(_agentBasePath , "conf","sysconf.ini")
        conf = ConfigParser.ConfigParser()
        conf.optionxform = str
        if os.path.exists(sys_conf):
            conf.read(sys_conf)
        if not conf.has_section('sys'):
            conf.add_section('sys')
        conf.set('sys', 'local_ip', ip)
        conf.write(open(sys_conf, 'w'))
        self.inner_ip = ip

    def plugin_init(self):
        return 0, 'OK'

    def handle_request(self,session):
        conf = AgentConfig()
        pb_session = pbSession(session,org=conf.get('base','client_id'),reverse = True)
        # long connection
        while True:
            # 接收请求
            code,req_info= pb_session.recv()
            if code != 0:
                break
            if req_info['op'] != 'request':
                pb_session.send_response(1003,"invalid request")
            req = req_info['data']
            code = 0
            msg = ""
            if req.cmd == "runCmd":
                from command.runCmd import runCmd
                run = runCmd()
                code,msg = run.process(req,pb_session)
            elif req.cmd == "runTool":
                from command.runTool import runTool
                run = runTool()
                code,msg = run.process(req,pb_session)
                #if code == run.TOOL_EXEC_OK:
                #    print "break"
                #    break
            elif req.cmd == "loadFile":
                from command.loadFile import loadFile
                run = loadFile()
                code,msg = run.process(req,session)
            else:
                code = 0
                msg="ok"
            ret = pb_session.send_response(code,msg)
        pb_session.close()


