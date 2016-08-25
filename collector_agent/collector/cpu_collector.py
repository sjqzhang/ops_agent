#!/usr/local/easyops/python/bin/python
#-*- coding: utf-8 -*-
import psutil
import os
import gevent
import platform

from collector.easy_collector import EasyCollector

class CpuCollector(EasyCollector):
    component = 'host'
    metric_define = {
        'cpu.used_total': {"type": "gauge", "unit": "%", "name": u'CPU总使用率', "info": ""},
        'cpu.used_sy': {"type": "gauge", "unit": "%", "name": u'系统态CPU使用率', "info": ""},
        'cpu.used_us': {"type": "gauge", "unit": "%", "name": u'用户态CPU使用率', "info": ""},
        'cpu.used_wa': {"type": "gauge", "unit": "%", "name": u'IO等待CPU使用率', "info": ""},
        # 'cpu.used_id': {"type": "gauge", "unit": "%", "name": u'空闲CPU率', "info": ""},
        # 'cpu.used_ni': {"type": "gauge", "unit": "%", "name": u'CPU使用率', "info": ""},
        # 'cpu.used_hi': {"type": "gauge", "unit": "%", "name": u'硬中断CPU使用率', "info": ""},
        # 'cpu.used_si': {"type": "gauge", "unit": "%", "name": u'软中断CPU使用率', "info": ""},
        # 'cpu.used_st': {"type": "gauge", "unit": "%", "name": u'stCPU使用率', "info": ""},
        'load.1': {"type": "gauge", "unit": "", "name": u'1分钟平均负载', "info": u""},
        'load.5': {"type": "gauge", "unit": "", "name": u'5分钟平均负载', "info": u""},
        'load.15': {"type": "gauge", "unit": "", "name": u'15分钟平均负载', "info": u""},
    }
    for i in range(64):#初始化64个核
        metric_define['cpu.cpu{0}_used'.format(i)] = {"type": "gauge", "unit": "%", "name": u'CPU{0}使用率'.format(i), "info": ""}

    last_cpu_times = None

    def check(self):
        data = {}
        # 20160725 windows下没有load指标
        if platform.system() != 'Windows':
            load = os.getloadavg()
            data.update({'load.1': load[0], 'load.5': load[1], 'load.15': load[2]})
        data.update({"cpu.used_total": int(psutil.cpu_percent())})
        # 获得单个CPU的使用率
        per_cpu = psutil.cpu_percent(percpu=True)
        # 是否只看CPU0就好了
        data.update({'cpu.cpu{0}_used'.format(i): int(val) for i,val in enumerate(per_cpu)})

        # 获得CPU的详情
        new_cpu_times = psutil.cpu_times()
        if self.last_cpu_times is not None:
            last_total_time = reduce(lambda s,x:s+x, self.last_cpu_times)
            now_total_time = reduce(lambda s,x:s+x, new_cpu_times)
            total_time = now_total_time - last_total_time
            data['cpu.used_sy'] = self._get_cpu_time('system', total_time, new_cpu_times)
            data['cpu.used_us'] = self._get_cpu_time('user', total_time, new_cpu_times)
            data['cpu.used_wa'] = self._get_cpu_time('iowait', total_time, new_cpu_times)
            # data['cpu.used_id'] = self._get_cpu_time('idle', total_time, new_cpu_times)
            # data['cpu.used_ni'] = self._get_cpu_time('nice', total_time, new_cpu_times)
            # data['cpu.used_hi'] = self._get_cpu_time('irq', total_time, new_cpu_times)
            # data['cpu.used_si'] = self._get_cpu_time('softirq', total_time, new_cpu_times)
            # data['cpu.used_st'] = self._get_cpu_time('steal', total_time, new_cpu_times)
        else:# 第一次启动
            self.last_cpu_times = new_cpu_times
            gevent.sleep(0.1)
            new_cpu_times = psutil.cpu_times()
            last_total_time = reduce(lambda s,x:s+x, self.last_cpu_times)
            now_total_time = reduce(lambda s,x:s+x, new_cpu_times)
            total_time = now_total_time - last_total_time
            data['cpu.used_sy'] = self._get_cpu_time('system', total_time, new_cpu_times)
            data['cpu.used_us'] = self._get_cpu_time('user', total_time, new_cpu_times)
            data['cpu.used_wa'] = self._get_cpu_time('iowait', total_time, new_cpu_times)

        self.last_cpu_times = new_cpu_times
        return data

    def _get_cpu_time(self, attr, total_time, stat):
        if not total_time:
            return 0
        new_att_time = getattr(stat, attr, 0)
        if not new_att_time:
            return None
        last_attr_time = getattr(self.last_cpu_times, attr, 0)
        if not last_attr_time:
            return None
        return (new_att_time - last_attr_time) * 100 / total_time


