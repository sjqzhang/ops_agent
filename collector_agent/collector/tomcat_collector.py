#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

from collector.jvm_collector import JvmCollector


class TomcatCollector(JvmCollector):
    component = 'tomcat'
    metric_define = {
        "threads.busy": {"type": "gauge", "unit": "", "name": u"忙碌线程数量", "info": ""},
        "threads.count": {"type": "gauge", "unit": "", "name": u"线程总数", "info": ""},
        "threads.max": {"type": "gauge", "unit": "", "name": u"可创建的线程上限", "info": ""},

        # Todo 未处理单位和换算
        "global.bytes_sent": {"type": "counter", "unit": "KB", "name": u"发送数据", "info": ""},
        "global.bytes_received": {"type": "counter", "unit": "KB", "name": u"接收数据", "info": ""},
        "global.error_count": {"type": "counter", "unit": "", "name": u"错误请求数", "info": ""},
        "global.request_count": {"type": "counter", "unit": "", "name": u"请求数", "info": ""},
        "global.max_time": {"type": "gauge", "unit": "", "name": u"请求处理的最大时间", "info": ""},
        "global.processing_time": {"type": "counter", "unit": "", "name": u"请求处理时间", "info": ""},

        # Todo 未处理成功率和换算
        "cache.access_count": {"type": "gauge", "unit": "", "name": u"String Cache访问次数", "info": ""},
        "cache.hits_count": {"type": "gauge", "unit": "", "name": u"String Cache命中次数", "info": ""},

        # Todo 未处理单位
        "servlet.processing_time": {"type": "gauge", "unit": "", "name": u"Servlet请求处理时间", "info": ""},
        "servlet.error_count": {"type": "gauge", "unit": "", "name": u"Servlet错误请求次数", "info": ""},
        "servlet.request_count": {"type": "gauge", "unit": "", "name": u"Servlet请求次数", "info": ""},

    }
    allow_undefined_metric = False
    metric_define.update(JvmCollector.metric_define)

    def check(self, config):
        data = {}

        data = super(TomcatCollector, self).check(config)

        # data process
        data["global.bytes_sent"] = self._byte_convert_to_kbyte(data.get("global.bytes_sent", 0))
        data["global.bytes_received"] = self._byte_convert_to_kbyte(data.get("global.bytes_received", 0))

        return data


