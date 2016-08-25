#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
import os

from collector.easy_collector import EasyCollector, EasyCollectorExcept
from libs.http_util import do_http


class NginxCollectorExcept(EasyCollectorExcept):
    code = 2000


class NginxCollector(EasyCollector):
    component = 'nginx'
    metric_define = {
        "conn.active": {"type": "gauge", "unit": "", "name": u'当前连接数', "info": ""},
        "conn.reading": {"type": "gauge", "unit": "", "name": u'正在读的连接数', "info": ""},
        "conn.writing": {"type": "gauge", "unit": "", "name": u'正在写的连接数', "info": ""},
        "conn.waiting": {"type": "gauge", "unit": "", "name": u'空闲连接数', "info": ""},
        "req.total": {"type": "counter", "unit": "", "name": u'请求总数', "info": ""},
        "req.accept": {"type": "counter", "unit": "", "name": u'已接受请求数', "info": ""},
        "req.handled": {"type": "counter", "unit": "", "name": u'已处理请求数', "info": ""},
    }
    allow_undefined_metric = False

    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 80)
        config.setdefault('uri', '/nginx_status')
        config.setdefault('timeout', 5)
        return config


    def _parse_nginx_status(self, rvalue):
        data = {}
        rval = rvalue.strip().split('\n')
        if len(rval) != 4:
            raise NginxCollectorExcept('nginx status return value format error: %s' %rvalue)
        data['conn.active'] = rval[0].split(':')[1].strip()
        val = rval[2].split()
        if len(val) != 3:
            raise NginxCollectorExcept('nginx status return value format error: %s' %rval[2])
        data['req.total'], data['req.accept'], data['req.handled'] = rval[2].split()
        val = rval[3].split()
        if len(val) != 6:
            raise NginxCollectorExcept('nginx status return value format error: %s' %rval[3])
        data['conn.reading'], data['conn.writing'], data['conn.waiting'] = val[1], val[3], val[5]
        return data

    def check(self, config):
        url = 'http://%s:%s/%s' %(config['host'], config['port'], config['uri'].strip('/'))
        rvalue = do_http('GET', url, timeout=config['timeout'])
        return self._parse_nginx_status(rvalue)


