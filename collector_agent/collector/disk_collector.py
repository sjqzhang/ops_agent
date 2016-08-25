#!/usr/local/easyops/python/bin/python
#-*- coding: utf-8 -*-
import psutil
import os

from collector.easy_collector import EasyCollector

class DiskCollector(EasyCollector):
    component = 'host'
    metric_define = {
        'disk.max_used_percent': {"type": "gauge", "unit": "%", "name": u'最大磁盘使用率', "info": ""},
        'disk.max_used_percent_mount': {"type": "text", "unit": "", "name": u'磁盘使用率最大的盘符', "info": ""},
        'disk.max_used': {"type": "gauge", "unit": "KB", "name": u'最大磁盘使用量', "info": ""},
        'disk.max_used_mount': {"type": "text", "unit": "", "name": u'磁盘使用量最大的盘符', "info": ""},
        'disk.min_free': {"type": "gauge", "unit": "KB", "name": u'最小磁盘可用量', "info": ""},
        'disk.min_free_mount': {"type": "text", "unit": "", "name": u'磁盘可用量最小的盘符', "info": ""},
        'disk.used_percent': {"type": "gauge", "unit": "%", "name": u'磁盘总使用率', "info": ""},
        'disk.used': {"type": "gauge", "unit": "KB", "name": u'磁盘总使用量', "info": ""},
        'disk.free': {"type": "gauge", "unit": "KB", "name": u'磁盘总可用量', "info": ""},
        'disk.total': {"type": "gauge", "unit": "KB", "name": u'磁盘总容量', "info": ""},
    }
    allow_undefined_metric = True

    def check(self):
        data = {
            'disk.max_used_percent': 0,
            'disk.max_used_percent_mount': '',
            'disk.max_used': 0,
            'disk.max_used_mount': '',
            'disk.min_free': 0,
            'disk.min_free_mount': '',
            'disk.used_percent': 0,
            'disk.used': 0,
            'disk.free': 0,
            'disk.total': 0,
        }
        partitions = psutil.disk_partitions(all=True)
        for partition in partitions:
            if partition.opts.upper() in ('CDROM', 'REMOVABLE'):
                continue
            mountpoint = partition.mountpoint
            usage = psutil.disk_usage(mountpoint)
            if usage.percent > data['disk.max_used_percent']:
                data['disk.max_used_percent'] = usage.percent
                data['disk.max_used_percent_mount'] = mountpoint
            if usage.used > data['disk.max_used']:
                data['disk.max_used'] = usage.used
                data['disk.max_used_mount'] = mountpoint
            if usage.free < data['disk.min_free'] or data['disk.min_free'] == 0:
                data['disk.min_free'] = usage.free
                data['disk.min_free_mount'] = mountpoint
            data['disk.used'] += usage.used
            data['disk.free'] += usage.free
            data['disk.total'] += usage.total
        data['disk.used_percent'] = data['disk.used']*100 / data['disk.total'] if data['disk.total'] else 0
        data['disk.max_used'] = data['disk.max_used'] / 1024
        data['disk.min_free'] = data['disk.min_free'] / 1024
        data['disk.used'] = data['disk.used'] / 1024
        data['disk.free'] = data['disk.free'] / 1024
        data['disk.total'] = data['disk.total'] / 1024
        return data







