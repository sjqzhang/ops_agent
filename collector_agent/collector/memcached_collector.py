#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-


from collector.easy_collector import EasyCollector
from pymemcache.client.base import Client


class MemcachedCollector(EasyCollector):
    component = 'memcached'
    metric_define = {
        "curr.connections": {"type": "gauge", "unit": "", "name": u'当前连接数', "info": ""},

        "cmd.get": {"type": "counter", "unit": "", "name": u'GET请求次数', "info": ""},
        "cmd.set": {"type": "counter", "unit": "", "name": u'SET请求次数', "info": ""},
        "cmd.flush": {"type": "counter", "unit": "", "name": u'FLUSH请求次数', "info": ""},

        "get.hits": {"type": "counter", "unit": "", "name": u'GET命中次数', "info": ""},
        "get.misses": {"type": "counter", "unit": "", "name": u'GET未命中次数', "info": ""},
        "hit.ratio": {"type": "gauge", "unit": "%", "name": u'GET命中率', "info": ""},

        "delete.hits": {"type": "counter", "unit": "", "name": u'DELETE命中次数', "info": ""},
        "delete.misses": {"type": "counter", "unit": "", "name": u'DELETE未命中次数', "info": ""},

        "incr.hits": {"type": "counter", "unit": "", "name": u'INCR命中次数', "info": ""},
        "incr.misses": {"type": "counter", "unit": "", "name": u'INCR未命中次数', "info": ""},

        "decr.hits": {"type": "counter", "unit": "", "name": u'DECR命中次数', "info": ""},
        "decr.misses": {"type": "counter", "unit": "", "name": u'DECR未命中次数', "info": ""},

        "cas.hits": {"type": "counter", "unit": "", "name": u'CAS命中次数', "info": ""},
        "cas.misses": {"type": "counter", "unit": "", "name": u'CAS未命中次数', "info": ""},
        "cas.badval": {"type": "counter", "unit": "", "name": u'CAS命中而版本已失效次数', "info": ""},

        "bytes.read": {"type": "counter", "unit": "KB", "name": u'读取的数据量', "info": ""},
        "bytes.written": {"type": "counter", "unit": "KB", "name": u'写入的数据量', "info": ""},
        "limit.maxbytes": {"type": "gauge", "unit": "KB", "name": u'最大缓存大小', "info": ""},

        "accepting.conns": {"type": "gauge", "unit": "", "name": u'当前处理连接数', "info": ""},

        "listen.disabled_num": {"type": "counter", "unit": "", "name": u'拒绝连接次数', "info": ""},

        "server.threads": {"type": "gauge", "unit": "", "name": u'处理线程数量', "info": ""},

        "curr.items": {"type": "gauge", "unit": "", "name": u'存储数据个数', "info": ""},

        "server.evictions": {"type": "counter", "unit": "", "name": u'缓存因空间不足而被剔除次数', "info": ""}
    }

    allow_undefined_metric = False
    last_cmd_get = None
    last_get_hits = None


    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 11211)
        config.setdefault('timeout', 5)
        return config

    def check(self, config):
        data = {}

        client = Client(
                (config["host"], config["port"]),
                connect_timeout=config["timeout"],
                timeout=config["timeout"]
        )
        memcached_stats = client.stats()

        # 遍历 memcache_stats 字典，做 key 的 split 转换处理，经过 split 后，分为 3 种情况进行处理：
        # 如果 split 后的数组元素长度为 1， 那么增加 server 前缀；
        # 如果 split 后的数组元素长度为 2， 那么什么都不需要做，直接split即可;
        # 如果 split 后的数组元素长度大于 2， 那么只需要 split 1 个字符即可；
        for key in memcached_stats.keys():
            split_len = len(key.split("_"))

            if split_len == 1:
                corrected_key = "server." + key
            elif split_len == 2:
                corrected_key = '.'.join(key.split("_"))
            else:
                corrected_key = '.'.join(key.split("_", 1))

            data[corrected_key] = self._convert_to_float(memcached_stats[key])

        # 数据处理
        total_cmd_get = self._convert_to_float(memcached_stats["cmd_get"])
        total_get_hits = self._convert_to_float(memcached_stats["get_hits"])

        if self.last_cmd_get is not None:
            cmd_get = total_cmd_get - self.last_cmd_get
            get_hits = total_get_hits - self.last_get_hits
            if cmd_get <= 0:
                data["hit.ratio"] = 0
            else:
                data["hit.ratio"] = self._decimal_convert_to_percent(get_hits / cmd_get)

        self.last_cmd_get = total_cmd_get
        self.last_get_hits = total_get_hits
        return data
