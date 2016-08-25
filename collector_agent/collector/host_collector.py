#!/usr/local/easyops/python/bin/python
#-*- coding: utf-8 -*-
import psutil
import os
import gevent
import traceback

from collector.easy_collector import EasyCollector
from collector.cpu_collector import CpuCollector
from collector.disk_collector import DiskCollector
from collector.io_collector import IoCollector
from collector.memory_collector import MemoryCollector
from collector.network_collector import NetworkCollector


class HostCollector(EasyCollector):
    data_id = 3100
    component = 'host'

    metric_define_version = 1.1

    def __init__(self, *args, **kwargs):
        super(HostCollector, self).__init__(*args, **kwargs)
        self.check_handler = {
            'cpu': CpuCollector(*args, **kwargs),
            'disk': DiskCollector(*args, **kwargs),
            'memory': MemoryCollector(*args, **kwargs),
            'network': NetworkCollector(*args, **kwargs),          
            'io': IoCollector(*args, **kwargs), # 比较消耗资源，放在最后
        }

        self.metric_define = {}
        for key, handler in self.check_handler.iteritems():
            self.metric_define.update(handler.metric_define)

    def plugin_init(self):
        for key, handler in self.check_handler.iteritems():
            handler.logger = self.logger
            handler.plugin_init()
        return super(HostCollector, self).plugin_init()

    def get_instances(self):
        return [{}]

    def check(self, config={}):
        res = {}
        for key, handler in self.check_handler.iteritems():
            try:
                res.update(handler.check())
            except:
                self.logger.error('collect %s error: %s' %(key, traceback.format_exc()))
            gevent.sleep()
        return res


    def shape_all_values(self, data):
        for key, handler in self.check_handler.iteritems():
            try:
                handler.shape_all_values(data)
            except:
                self.logger.error(traceback.format_exc())


# if __name__ == '__main__':
#     host = HostCollector('', '', '')
#     print host.metric_define
#     print host.check()
