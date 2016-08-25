# encoding=utf-8

import sys
import time
import gevent
from easy_plugin import EasyPlugin
from pkg.script.common import runShell

import logging
import logging.config
import os

_cur_path = os.path.dirname(os.path.abspath(__file__))
_agentBasePath = os.path.dirname(_cur_path)
logging.config.fileConfig(os.path.join(_agentBasePath,"conf","logAgent.conf"))
logger = logging.getLogger("logAgent")


class ClearFile(EasyPlugin):
    def __init__(self, application, name, config):
        EasyPlugin.__init__(self, application, name, config)
        
    def handle_timer(self):
        logger.info('clear file start...')
        st = time.time()
        script = "%s/easyops.py clear all" % (os.path.join(_agentBasePath, "pkg", "script"))
        code, msg = runShell(script)
        timecost = time.time() - st
        if code:
            logger.error(u'clear file end, timecost: %s code: %s msg: %s' %(timecost, code, msg))
        else:
            logger.info(u'clear file end, timecost: %s code: %s msg: %s' %(timecost, code, msg))

    def plugin_init(self):
        return 0, 'OK'


