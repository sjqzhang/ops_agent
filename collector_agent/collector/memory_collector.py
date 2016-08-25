#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
import psutil
import os

from collector.easy_collector import EasyCollector


class MemoryCollector(EasyCollector):
    component = 'host'
    metric_define = {
        'mem.available': {'type': 'gauge', 'unit': 'KB', 'name': u'可用内存', 'info': u'free+cached+buffer'},
        'mem.free': {'type': 'gauge', 'unit': 'KB', 'name': u'未使用内存', 'info': u'不包括cached和buffer'},
        'mem.percent': {'type': 'gauge', 'unit': '%', 'name': u'已使用内存比例', 'info': '(总内存量 - 可用内存) / 总内存量 * 100'},
        'mem.total': {'type': 'gauge', 'unit': 'KB', 'name': u'总内存量', 'info': ''},
        'mem.used': {'type': 'gauge', 'unit': 'KB', 'name': u'已使用内存', 'info': ''},
        'mem.cached': {'type': 'gauge', 'unit': 'KB', 'name': u'cached内存', 'info': ''},
        'mem.buffers': {'type': 'gauge', 'unit': 'KB', 'name': u'buffers内存', 'info': ''},

        # 'mem.active': {'type': 'gauge', 'unit': 'KB', 'name': '正在用或最近被用过的内存', 'info': ''},
        # 'mem.inactive': {'type': 'gauge', 'unit': 'KB', 'name': '完全没用过的内存', 'info': ''},

        'mem.swap_total': {'type': 'gauge', 'unit': 'KB', 'name': u'总SWAP内存', 'info': ''},
        'mem.swap_used': {'type': 'gauge', 'unit': 'KB', 'name': u'已使用SWAP内存', 'info': ''},
        'mem.swap_free': {'type': 'gauge', 'unit': 'KB', 'name': u'未使用SWAP内存', 'info': ''},
        'mem.swap_percent': {'type': 'gauge', 'unit': '%', 'name': u'SWAP内存使用率', 'info': ''},
    }
    
    def check(self):
        virtual_memory = psutil.virtual_memory()
        _virtual_memory = {'mem.%s' % key: getattr(virtual_memory, key) / 1024 for key in virtual_memory._fields if key != 'percent'}
        swap_memory = psutil.swap_memory()
        _swap_memory = {'mem.swap_%s' % key: getattr(swap_memory, key) / 1024 for key in swap_memory._fields if key != 'percent'}
        _virtual_memory['mem.percent'] = virtual_memory.percent
        _swap_memory['mem.swap_percent'] = swap_memory.percent
        return dict(_virtual_memory, **_swap_memory)
