#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import re

from collector.easy_collector import EasyCollector
from libs.http_util import do_http


class ApacheCollector(EasyCollector):
    component = 'apache'

    metric_define = {
        "server.up_time": {"type": "gauge", "unit": "s", "name": u'运行时间', "info": "单位: second"},

        "server.accesses": {"type": "counter", "unit": "", "name": u'访问次数', "info": ""},
        "server.traffic": {"type": "counter", "unit": "KB", "name": u'请求流量统计', "info": "单位: KByte"},

        "cpu.user": {"type": "gauge", "unit": "%", "name": u'用户态CPU使用率', "info": ""},
        "cpu.system": {"type": "gauge", "unit": "%", "name": u'内核态CPU使用率', "info": ""},

        "request.request_per_second": {"type": "gauge", "unit": "requests/second", "name": u'每秒访问请求', "info": ""},
        "request.kbyte_per_second": {"type": "gauge", "unit": "KByte/second", "name": u'每秒流量', "info": ""},
        "request.kbyte_per_request": {"type": "gauge", "unit": "KByte/request", "name": u'每个请求流量', "info": ""},

        "worker.processing_requests": {"type": "gauge", "unit": "", "name": u'正在处理请求数量', "info": ""},
        "worker.idle": {"type": "gauge", "unit": "", "name": u'空闲worker数量', "info": ""}
    }

    allow_undefined_metric = False

    convert_fun = {
        'GB': lambda x: x * 1024 * 1024,
        'MB': lambda x: x * 1024,
        'B': lambda x: x / 1024,
        'KB': lambda x: x,
    }

    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 80)
        config.setdefault('uri', '/server-status')
        return config


    def _convert_to_kbyte(self, value, unit):
        value = self._convert_to_float(value)
        return self.convert_fun[unit.upper()](value)

    def _convert_to_second(self, value, unit):
        value = self._convert_to_float(value)
        if unit == "days":
            return value * 24 * 3600
        elif unit == "hours":
            return value * 3600
        elif unit == "minutes":
            return value * 60
        else:
            return value

    def check(self, config):
        data = {}
        url = 'http://%s:%s/%s' % (config['host'], config['port'], config['uri'].strip('/'))
        time_out = config.get("timeout", 5)
        apache_status = do_http('GET', url, params={}, timeout=time_out)

        status_array = apache_status.strip().replace("<dt>", "").replace("</dt>", "").splitlines()
        for i in range(len(status_array)):
            # accesses and traffic
            match_obj = \
                re.search(r'(Total accesses): (.+) - (Total Traffic): (.+) (B|kB|MB|GB)', status_array[i])
            if match_obj:
                data["server.accesses"] = match_obj.group(2)
                data["server.traffic"] = self._convert_to_kbyte(match_obj.group(4), match_obj.group(5))

            # request
            match_obj = re.search(r'(.+) (requests/sec) - (.+) (B|kB|MB|GB)/second - (.+) (B|kB|MB|GB)/request',
                                  status_array[i])
            if match_obj:
                data["request.request_per_second"] = match_obj.group(1)
                data["request.kbyte_per_second"] = self._convert_to_kbyte(match_obj.group(3), match_obj.group(4))
                data["request.kbyte_per_request"] = self._convert_to_kbyte(match_obj.group(5), match_obj.group(6))

            # worker status
            match_obj = re.search(r'(.+) requests currently being processed, (.+) idle workers', status_array[i])
            if match_obj:
                data["worker.processing_requests"] = match_obj.group(1)
                data["worker.idle"] = match_obj.group(2)

            # up time
            match_obj = re.search(r'Server uptime: (.+)', status_array[i])
            if match_obj:
                up_time = match_obj.group(1).split()

                data["server.up_time"] = 0
                if isinstance(up_time, list):
                    if len(up_time) == 2:
                        data["server.up_time"] = self._convert_to_float(up_time[0])
                    else:
                        for j in range(0, len(up_time), 2):
                            data["server.up_time"] += self._convert_to_second(up_time[j], up_time[j + 1])

            # cpu usage
            match_obj = re.search(r'(CPU Usage:) (u)(.+) (s)(.+)', status_array[i])
            if match_obj:
                data["cpu.user"] = match_obj.group(3)
                data["cpu.system"] = match_obj.group(5)

        # Float 处理
        for key in data.keys():
            data[key] = self._convert_to_float(data[key])

        return data



