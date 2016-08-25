#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
from pymongo import ReadPreference

from collector.easy_collector import EasyCollector


class MongodbCollector(EasyCollector):
    component = 'mongodb'

    metric_define = {
        # mongodb 的整体信息
        "server.uptime": {"type": "gauge", "unit": "s", "name": u'服务运行时间', "info": ""},

        # mongodb 的 global lock 信息
        "globallock.totaltime": {"type": "gauge", "unit": "s",
                                 "name": u'全局锁创建以来经过时间', "info": u"服务启动并且创建全局锁, 到目前为止所经过的时间, 大约和 server.uptime 相等"},
        "globallock.activeclients_readers": {"type": "gauge", "unit": "", "name": u'正在读的客户端数', "info": ""},
        "globallock.activeclients_total": {"type": "gauge", "unit": "", "name": u'所有活动的客户端数', "info": ""},
        "globallock.activeclients_writers": {"type": "gauge", "unit": "", "name": u'正在写的客户端数', "info": ""},
        "globallock.currentqueue_readers": {"type": "gauge", "unit": "", "name": u'等待读锁的操作数', "info": ""},
        "globallock.currentqueue_total": {"type": "gauge", "unit": "", "name": u'等待锁的操作数', "info": ""},
        "globallock.currentqueue_writers": {"type": "gauge", "unit": "", "name": u'等待写锁的操作数', "info": ""},

        # mongodb 的 connections 信息
        "connections.current": {"type": "gauge", "unit": "", "name": u'当前连接数', "info": ""},
        "connections.available": {"type": "gauge", "unit": "", "name": u'可用连接数', "info": ""},

        # mongodb 的 asserts 信息
        "asserts.regular": {"type": "counter", "unit": "", "name": u'常规断言数', "info": ""},
        "asserts.warning": {"type": "counter", "unit": "", "name": u'警告断言数', "info": ""},
        "asserts.msg": {"type": "counter", "unit": "", "name": u'消息断言数', "info": ""},
        "asserts.user": {"type": "counter", "unit": "", "name": u'用户断言数', "info": ""},
        "asserts.rollovers": {"type": "counter", "unit": "", "name": u'断言次数重置次数', "info": ""},

        # mongodb 的 extra_info
        "extra.info_heap_usage_bytes": {"type": "gauge", "unit": "KB", "name": u'堆空间大小', "info": ""},
        "extra.info_page_faults": {"type": "counter", "unit": "", "name": u'内存页错误次数', "info": ""},

        # mongodb 的 memory 信息
        "mem.resident": {"type": "gauge", "unit": "KB", "name": u'物理内存大小', "info": ""},
        "mem.virtual": {"type": "gauge", "unit": "KB", "name": u'虚拟内存大小', "info": ""},
        "mem.mappedwithjournal": {"type": "gauge", "unit": "KB", "name": u'存储日志使用的共享内存大小',
                                  "info": ""},

        # mongodb 的相关 metric 信息
        # cursor 信息
        "metrics.cursor_timedout": {"type": "counter", "unit": "", "name": u'超时cursor数', "info": ""},
        "metrics.cursor_open_total": {"type": "gauge", "unit": "", "name": u'打开cursor数', "info": ""},
        "metrics.cursor_open_notimeout": {"type": "gauge", "unit": "",
                                          "name": u'设置为不超时的cursor数', "info": u"设定了DBQuery.Option.noTimeout"},

        # metric document
        "metrics.document_deleted": {"type": "counter", "unit": "", "name": u'删除次数', "info": ""},
        "metrics.document_inserted": {"type": "counter", "unit": "", "name": u'插入次数', "info": ""},
        "metrics.document_returned": {"type": "counter", "unit": "", "name": u'查询次数', "info": ""},
        "metrics.document_updated": {"type": "counter", "unit": "", "name": u'更新次数', "info": ""},

        # metric operation
        "metrics.operation_fastmod": {"type": "counter", "unit": "", "name": u'快速更新次数', "info": u"更新操作没有对集合大小或对索引修改的次数"},
        "metrics.operation_idhack": {"type": "counter", "unit": "", "name": u'以_id为过滤条件的查询次数', "info": ""},
        "metrics.operation_scanandorder": {"type": "counter", "unit": "", "name": u'无法用索引来排序的查询次数', "info": ""},

        # metric queryExecutor
        "metrics.queryexecutor_scanned": {"type": "counter", "unit": "", "name": u'查询时用到的索引数目', "info": ""},

        # metric record
        "metrics.record_moves": {"type": "counter", "unit": "", "name": u'文档被移动的次数', "info": ""},

        # metric replication apply
        "metrics.repl_apply_batches_num": {"type": "counter", "unit": "",
                                           "name": u'对所有数据库执行的批处理的个数',
                                           "info": u'主从同步时, 需要应用 oplog 的操作, '
                                                   u'这些操作使用多线程进行批量处理, 从而增加同步效率, 这里指多线程批量应用的次数'},
        "metrics.repl_apply_batches_totalmillis": {"type": "counter", "unit": "s", "name": u'批处理用时', "info": ""},
        "metrics.repl_apply_ops": {"type": "counter", "unit": "", "name": u'oplog操作次数', "info": ""},

        # metric replication buffer
        "metrics.repl_buffer_count": {"type": "gauge", "unit": "",
                                      "name": u'oplog缓存操作数',
                                      "info": u'进行批量处理前, MongoDB 会把需要该批次需要执行的 oplog 操作条目放到 oplog buffer 中,'
                                              u'这里指 oplog buffer 中缓存的操作条目的数量'},
        "metrics.repl_buffer_sizebytes": {"type": "gauge", "unit": "KB", "name": u'oplog缓存大小', "info": ""},

        # metric replication network
        "metrics.repl_network_bytes": {"type": "counter", "unit": "KB", "name": u'主节点读取的数据量', "info": u"发生在主从同步"},
        "metrics.repl_network_getmores_num": {"type": "counter", "unit": "",
                                              "name": u'getmores操作的次数', "info": u"主从同步从额外的set读取到的getmores操作的次数"},
        "metrics.repl_network_getmores_totalmillis": {"type": "counter", "unit": "s",
                                                      "name": u'getmores操作用时', "info": u"发生在主从同步"},
        "metrics.repl_network_ops": {"type": "counter", "unit": "", "name": u'从主节点读取到的操作条目数量', "info": u"发生在主从同步"},
        "metrics.repl_network_readerscreated": {"type": "counter", "unit": "",
                                                "name": u'创建的oplog查询进程数', "info": u"发生在主从同步"},

        # metric replication oplog
        "metrics.repl_oplog_insert_num": {"type": "counter", "unit": "", "name": u'oplog插入操作数', "info": ""},
        "metrics.repl_oplog_insert_totalmillis": {"type": "counter", "unit": "s",
                                                  "name": u'oplog插入操作用时', "info": ""},
        "metrics.repl_oplog_insertbytes": {"type": "counter", "unit": "KB", "name": u'oplog插入的数据量', "info": ""},

        # metric replication preload
        "metrics.repl_preload_docs_num": {"type": "counter", "unit": "",
                                          "name": u'预读阶段加载到内存的文档数', "info": u"发生在主从同步"},
        "metrics.repl_preload_docs_totalmillis": {"type": "counter", "unit": "s",
                                                  "name": u'预读阶段加载文档到内存用时', "info": u"发生在主从同步"},
        "metrics.repl_preload_indexes_num": {"type": "counter", "unit": "",
                                             "name": u'预读阶段加载到内存的索引数', "info": u"发生在主从同步"},
        "metrics.repl_preload_indexes_totalmillis": {"type": "counter", "unit": "s",
                                                     "name": u'预读阶段加载索引到内存用时', "info": u"发生在主从同步"},

        # metric storage
        "metrics.storage_freelist_search_bucketexhausted": {"type": "counter", "unit": "",
                                                            "name": u'分配bucket失败数',
                                                            "info": u'分配空间时, freelist 中找不到合适的bucket来存储这个条目的次数'},
        "metrics.storage_freelist_search_requests": {"type": "counter", "unit": "", "name": u'分配bucket请求数',
                                                     "info": ""},
        "metrics.storage_freelist_search_scanned": {"type": "counter", "unit": "",
                                                    "name": u'搜索到的可用bucket的数量', "info": ""},

        # metric ttl
        "metrics.ttl_deleteddocuments": {"type": "counter", "unit": "", "name": u'使用TTL索引删除的文档数', "info": ""},
        "metrics.ttl_passes": {"type": "counter", "unit": "", "name": u'使用TTL索引删除文档的操作数', "info": ""},

        # network
        "network.bytesin": {"type": "counter", "unit": "", "name": u'网络入流量', "info": u""},
        "network.bytesout": {"type": "counter", "unit": "", "name": u'网络出流量', "info": ""},
        "network.numrequests": {"type": "counter", "unit": "", "name": u'总请求数', "info": ""},

        # opcounters
        "opcounters.insert": {"type": "counter", "unit": "", "name": u'插入次数', "info": ""},
        "opcounters.query": {"type": "counter", "unit": "", "name": u'查询次数', "info": ""},
        "opcounters.update": {"type": "counter", "unit": "", "name": u'更新次数', "info": ""},
        "opcounters.delete": {"type": "counter", "unit": "", "name": u'删除次数', "info": ""},
        "opcounters.getmore": {"type": "counter", "unit": "", "name": u'getmore次数', "info": ""},
        "opcounters.command": {"type": "counter", "unit": "", "name": u'执行命令次数', "info": ""},

        # opcountersRepl
        "opcountersrepl.insert": {"type": "counter", "unit": "", "name": u'主从同步时插入次数', "info": ""},
        "opcountersrepl.query": {"type": "counter", "unit": "", "name": u'主从同步时查询次数', "info": ""},
        "opcountersrepl.update": {"type": "counter", "unit": "", "name": u'主从同步时更新次数', "info": ""},
        "opcountersrepl.delete": {"type": "counter", "unit": "", "name": u'主从同步时删除次数', "info": ""},
        "opcountersrepl.getmore": {"type": "counter", "unit": "", "name": u'主从同步时getmores次数', "info": ""},
        "opcountersrepl.command": {"type": "counter", "unit": "", "name": u'主从同步时执行命令次数', "info": ""},

        # dbStats
        "dbstats.collections": {"type": "gauge", "unit": "", "name": u'集合个数', "info": ""},
        "dbstats.objects": {"type": "gauge", "unit": "", "name": u'对象个数', "info": ""},
        "dbstats.avgobjsize": {"type": "gauge", "unit": "KB", "name": u'对象的平均大小', "info": ""},
        "dbstats.datasize": {"type": "gauge", "unit": "KB", "name": u'对象总大小', "info": u""},
        "dbstats.storagesize": {"type": "gauge", "unit": "KB",
                                "name": u'对象总大小(包括预分配的空间)', "info": u"根据padding factor的变化, 这个值一般会比 datasize 要大"},
        "dbstats.numextents": {"type": "gauge", "unit": "", "name": u'extent数量', "info": ""},
        "dbstats.indexes": {"type": "gauge", "unit": "", "name": u'索引的数量', "info": ""},
        "dbstats.indexsize": {"type": "gauge", "unit": "", "name": u'索引的大小', "info": ""},
        "dbstats.filesize": {"type": "gauge", "unit": "", "name": u'数据库文件大小',
                             "info": ""},
        "dbstats.nssizemb": {"type": "gauge", "unit": "KB", "name": u'namespace文件大小', "info": ""}
    }

    allow_undefined_metric = False

    db = None
    corrected_key = ""
    new_dict = {}


    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 11211)
        config.setdefault('timeout', 10)
        return config


    def create_db_connection(self, config):
        if config.get('username') and config.get('password'):
            auth_url = '%s:%s@' % (config['username'], config['password'])
        else:
            auth_url = ''
        server_url = 'mongodb://%s%s:%s' % (auth_url, config['host'], config['port'])
        ssl_params = {
            'ssl': config.get('ssl', None),
            'ssl_keyfile': config.get('ssl_keyfile', None),
            'ssl_certfile': config.get('ssl_certfile', None),
            'ssl_cert_reqs': config.get('ssl_cert_reqs', None),
            'ssl_ca_certs': config.get('ssl_ca_certs', None)
        }

        for key, param in ssl_params.items():
            if param is None:
                del ssl_params[key]

        # configuration a URL, mongodb://user:pass@server/db
        time_out = config.get("timeout", 5)
        client = MongoClient(
                server_url,
                socketTimeoutMS=5000,
                connectTimeoutMS=time_out * 1000,
                serverSelectionTimeoutMS=5000,
                read_preference=ReadPreference.PRIMARY_PREFERRED,
                **ssl_params
        )

        self.db = client['admin']

    def transform_dict(self, dict_a):
        if isinstance(dict_a, dict):
            for key, value in dict_a.items():
                self.corrected_key = self.corrected_key + "-" + key
                self.transform_dict(value)
                pos = self.corrected_key.rfind("-")
                self.corrected_key = self.corrected_key[:pos]
        else:
            self.new_dict[self.corrected_key] = dict_a

    def check(self, config):
        # initialize the mongodb connection
        self.create_db_connection(config)

        data = {}

        # collect server status, set locks and wiredTiger close
        server_status = self.db.command("serverStatus", 1, locks=0, wiredTiger=0)

        # reset key and value
        self.corrected_key = ""
        self.new_dict = {}
        self.transform_dict(server_status)

        for key, value in self.new_dict.items():
            key_len = len(key.split("-"))
            if key_len == 2:
                new_key = "server." + key.lower().split("-")[1]

            elif key_len > 2:
                new_key = ".".join(key.lower().replace("-", "_").split("_", 2)).replace(".", "", 1)

            data[new_key] = value

        # collect db stats, set scale to 1024 Byte(1 KByte)
        stats = self.db.command("dbStats", 1, scale=1024)
        for key, value in stats.items():
            corrected_key = "dbstats." + key.lower()
            data[corrected_key] = value

        # covert microsecond to second
        data["globallock.totaltime"] = self._millisecond_convert_to_second(data.get("globallock.totaltime", 0))
        data["metrics.repl_apply_batches_totalmillis"] = \
            self._millisecond_convert_to_second(data.get("metrics.repl_apply_batches_totalmillis", 0))
        data["metrics.repl_network_getmores_totalmillis"] = \
            self._millisecond_convert_to_second(data.get("metrics.repl_network_getmores_totalmillis", 0))
        data["metrics.repl_oplog_insert_totalmillis"] = \
            self._millisecond_convert_to_second(data.get("metrics.repl_oplog_insert_totalmillis", 0))
        data["metrics.repl_preload_docs_totalmillis"] = \
            self._millisecond_convert_to_second(data.get("metrics.repl_preload_docs_totalmillis", 0))
        data["metrics.repl_preload_indexes_totalmillis"] = \
            self._millisecond_convert_to_second(data.get("metrics.repl_preload_indexes_totalmillis", 0))

        # covert byte to kbyte
        data["extra.info_heap_usage_bytes"] = self._byte_convert_to_kbyte(data.get("extra.info_heap_usage_bytes", 0))
        data["metrics.repl_buffer_sizebytes"] = \
            self._byte_convert_to_kbyte(data.get("metrics.repl_buffer_sizebytes", 0))
        data["metrics.repl_network_bytes"] = self._byte_convert_to_kbyte(data.get("metrics.repl_network_bytes", 0))
        data["metrics.repl_oplog_insertbytes"] = \
            self._byte_convert_to_kbyte(data.get("metrics.repl_oplog_insertbytes", 0))
        data["network.bytesin"] = self._byte_convert_to_kbyte(data.get("network.bytesin", 0))
        data["network.bytesout"] = self._byte_convert_to_kbyte(data.get("network.bytesout", 0))
        data["dbstats.avgobjsize"] = self._byte_convert_to_kbyte(data.get("dbstats.avgobjsize", 0))
        data["dbstats.datasize"] = self._byte_convert_to_kbyte(data.get("dbstats.datasize", 0))
        data["dbstats.storagesize"] = self._byte_convert_to_kbyte(data.get("dbstats.storagesize", 0))
        data["dbstats.indexsize"] = self._byte_convert_to_kbyte(data.get("dbstats.indexsize", 0))
        data["dbstats.filesize"] = self._byte_convert_to_kbyte(data.get("dbstats.filesize", 0))

        # covert mbyte to kbyte
        data["mem.resident"] = self._mbyte_convert_to_kbyte(data.get("mem.resident", 0))
        data["mem.virtual"] = self._mbyte_convert_to_kbyte(data.get("mem.virtual", 0))
        data["mem.mappedwithjournal"] = self._mbyte_convert_to_kbyte(data.get("mem.mappedwithjournal", 0))
        data["dbstats.nssizemb"] = self._mbyte_convert_to_kbyte(data.get("dbstats.nssizemb", 0))

        return data
