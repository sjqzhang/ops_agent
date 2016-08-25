# encoding=utf-8

import sys
import time
import gevent
from easy_plugin import EasyPlugin
from pkg.script.common import runShell
from libs.config import AgentConfig
import httplib

import logging
import logging.config
import os

_cur_path = os.path.dirname(os.path.abspath(__file__))
_agentBasePath = os.path.dirname(_cur_path)
logging.config.fileConfig(os.path.join(_agentBasePath,"conf","logAgent.conf"))
logger = logging.getLogger("logAgent")


class AutoUpdate(EasyPlugin):
    def __init__(self, application, name, config):
        EasyPlugin.__init__(self, application, name, config)

    def handle_timer(self):
        ret, new_version = self.get_version()
        if ret != 0:
            logger.info("get version error," + str(ret))
            return 1,'get version error'
        # compare version
        if not self.compare_version(new_version):
            # download new version
            logger.info('start to update agent to %s' %new_version)
            self.get_package(new_version)


    def plugin_init(self):
        conf = AgentConfig()
        self._version = conf.get('base','version')
        conf = AgentConfig()
        self.serverList = conf.get('command','servers')
        return 0, 'OK'

    def get_version(self):
        ip_port = "%s:%s"%(self.serverList[0]['ip'],'80')
        headers = {'Host': 'download.easyops-only.com', 'Content-type': 'application/json'}
        try:
            conn = httplib.HTTPConnection(ip_port, timeout=3)
            conn.request('GET', '/version', headers=headers)
            response = conn.getresponse()
            status = response.status
            new_version = response.read()
            conn.close()
        except Exception,e:
            logger.error("get version failed")
            conn.close()
            new_version = ""
            status = 405

        new_version = new_version.strip()
        if status == 200:
            return (0, new_version)
        else:
            return (1, 'get version failed')

    def get_package(self, version):
        ip_port = "%s:%s"%(self.serverList[0]['ip'],'80')
        shell_script = """
        curl -H 'Host: download.easyops-only.com?v=%s' http://%s/agent_install.sh | bash
        """ % (version, ip_port)
        ret = runShell(shell_script)

    def compare_version(self, new_version):
        # 空字符表示关闭自动升级
        if not new_version:
            return True
        return self._version == new_version
