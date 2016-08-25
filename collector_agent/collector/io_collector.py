#!/usr/local/easyops/python/bin/python
#-*- coding: utf-8 -*-
import os
import psutil
import gevent
import time
import platform

from utils.cmd_util import get_cmd_output
from utils import platform_util
from collector.easy_collector import EasyCollector

class IoCollector(EasyCollector):
    component = 'host'

    metric_define = {
        'io.w_s': {'type': 'gauge', 'unit': '', 'name': u'磁盘写次数', 'info': ''},
        'io.wkbyte_s': {'type': 'gauge', 'unit': 'KB/s', 'name': u'磁盘写字节数', 'info': ''},
        'io.avgrq_sz': {'type': 'gauge', 'unit': 'sector', 'name': u'平均IO操作的扇区大小', 'info': u'平均1次IO操作的扇区大小，包括读和写'},
        'io.r_s': {'type': 'gauge', 'unit': '', 'name': u'磁盘读次数', 'info': ''},
        'io.rkbyte_s': {'type': 'gauge', 'unit': 'KB/s', 'name': u'磁盘读字节数', 'info': ''},
        'io.await': {'type': 'gauge', 'unit': 'ms', 'name': u'平均IO操作时间(含队列等待时间)', 'info': u'平均每次IO操作时间，包括队列等待时间和真正磁盘操作时间，一般应小于5ms'},
        'io.svctm': {'type': 'gauge', 'unit': 'ms', 'name': u'平均IO操作时间', 'info': ''},
        'io.queue_time_percent': {'type': 'gauge', 'unit': '%', 'name': u'平均IO操作等待时间比例', 'info': u'平均每次IO操作的等待时间比重，这个超过50%说明每次IO的操作都花费了大量时间在IO队列等待上'},
        'io.util': {'type': 'gauge', 'unit': '%', 'name': u'磁盘IO率', 'info': u'一秒中有用于IO操作的时间比例，取最大值的那个盘'},
    }

    last_stat = {}
    last_cpu_time = 0
    cpu_count = psutil.cpu_count(logical=True)

    def check(self):
        # 也可以做成与上一次结果相减的方式，而不用一次就调用两次
        # if platform_util.is_linux():
        #     data_per_disk, count = self.get_linux_iostat()
        # else:
        # 测试数据看，这种计算方式与iostat很相近，故直接采用这种方式。Alren 2016-03-11
        data_per_disk, count = self.get_other_iostat()
        if count: # 这里，LXC挂载的那个盘会发现不了，disk_io_counters
            data = {k: v/count for k,v in data_per_disk.iteritems() if k != 'io.util'}
            data['io.util'] = data_per_disk['io.util']
        else:
            data = data_per_disk
        return data


    def sum_cpu_time(self, cpu_time):
        if platform.system() == 'Windows':
            return cpu_time.user + cpu_time.system + cpu_time.idle
        else:
            return cpu_time.user + cpu_time.system + cpu_time.idle + cpu_time.iowait

    def get_other_iostat(self):
        curr_stat = psutil.disk_io_counters(True)
        curr_cpu_time = self.sum_cpu_time(psutil.cpu_times()) / self.cpu_count
        if self.last_cpu_time == 0: #刚启动
            self.last_stat = curr_stat
            self.last_cpu_time = curr_cpu_time
            return {}, 0
        data_per_disk = {k: 0 for k in self.metric_define}
        count = 0
        ts = curr_cpu_time - self.last_cpu_time
        for disk, nval in curr_stat.iteritems():
            oval = self.last_stat.get(disk)# 有新增磁盘
            if not oval:
                continue
            total_time = nval.write_time - oval.write_time + nval.read_time - oval.read_time
            total_count = nval.write_count - oval.write_count + nval.read_count - oval.read_count
            if not total_count: # 该磁盘没有IO操作，不参与平均
                continue
            data_per_disk['io.w_s'] += (nval.write_count - oval.write_count) / ts
            data_per_disk['io.wkbyte_s'] += (nval.write_bytes - oval.write_bytes) / 1024 / ts
            data_per_disk['io.r_s'] += (nval.read_count - oval.read_count) / ts
            data_per_disk['io.rkbyte_s'] += (nval.read_bytes - oval.read_bytes) / 1024 / ts
            data_per_disk['io.await'] += total_time / total_count if total_count else 0.0
            if hasattr(oval, 'busy_time'):# linux下psutil==4.0.0才有busy_time
                data_per_disk['io.svctm'] += (nval.busy_time - oval.busy_time) / total_count if total_count else 0.0
                io_util = (nval.busy_time - oval.busy_time) * 100.0 / (ts*1000)
                if io_util > data_per_disk['io.util']:# 取最大那个
                    data_per_disk['io.util'] = io_util if io_util < 100 else 100
                data_per_disk['io.queue_time_percent'] = (data_per_disk['io.await'] - data_per_disk['io.svctm']) * 100 / data_per_disk['io.await'] if data_per_disk['io.await'] else 0
            count += 1

        self.last_stat = curr_stat
        self.last_cpu_time = curr_cpu_time
        return data_per_disk, count

    def get_linux_iostat(self):
        cmd = ['iostat', '-x', '1', '2', '-d', '-k']
        try:
            output = get_cmd_output(cmd)
        except OSError,e:
            self.logger.error('not found iostat command, would not collect io metric')
            return {}, 0
        data_per_disk = {k: 0 for k in self.metric_define}
        count = 0
        validate = False
        for line in output.split('\n')[3:]:
            if not validate and not line.startswith('Device:'):# 采集使用第2次的，第1次的都是固定的
                continue
            elif line.startswith('Device:'):
                validate = True
                continue
            fields = line.split()
            if len(fields) != 12:
                continue
            count += 1
            data_per_disk['io.r_s'] += float(fields[3])
            data_per_disk['io.w_s'] += float(fields[4])
            data_per_disk['io.rkbyte_s'] += float(fields[5])
            data_per_disk['io.wkbyte_s'] += float(fields[6])
            data_per_disk['io.avgrq_sz'] += float(fields[7])
            data_per_disk['io.await'] += float(fields[9])
            data_per_disk['io.svctm'] += float(fields[10])
            util = float(fields[11])
            if util > data_per_disk['io.util']:
                data_per_disk['io.util'] = util
        data_per_disk['io.queue_time_percent'] = (data_per_disk['io.await'] - data_per_disk['io.svctm']) * 100 / data_per_disk['io.await'] if data_per_disk['io.await'] else 0
        return data_per_disk, count











