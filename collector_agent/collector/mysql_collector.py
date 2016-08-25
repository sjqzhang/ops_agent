#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import pymysql

from collector.easy_collector import EasyCollector


class MysqlCollector(EasyCollector):
    component = 'mysql'
    metric_define = {
        "aborted.clients": {"type": "counter", "unit": "", "name": u'中断连接数', "info": u"由于某种原因客户程序不能正常关闭连接而导致失败的连接的数量"},
        "aborted.connects": {"type": "counter", "unit": "", "name": u'试图连接到MYSQL失败的次数', "info": ""},

        "binlog.cache_disk_use": {"type": "counter", "unit": "",
                                  "name": u'用临时文件保存binlog的事务数', "info": u"binog.cache_disk_use: 使用 binlog cache 但超过 binlog_cache_size 值并使用临时文件来保存事务中的语句的事务数量"},

        "binlog.cache_use": {"type": "counter", "unit": "", "name": u'binlog cache中的事务数量', "info": ""},

        "com.delete": {"type": "counter", "unit": "", "name": u'delete执行次数', "info": ""},
        "com.delete_multi": {"type": "counter", "unit": "", "name": u'delete_multi执行次数', "info": ""},
        "com.insert": {"type": "counter", "unit": "", "name": u'insert执行次数', "info": ""},
        "com.insert_select": {"type": "counter", "unit": "", "name": u'insert_select执行次数', "info": ""},
        "com.select": {"type": "counter", "unit": "", "name": u'select执行次数', "info": ""},
        "com.update": {"type": "counter", "unit": "", "name": u'update执行次数', "info": ""},
        "com.update_multi": {"type": "counter", "unit": "", "name": u'update_multi执行次数', "info": ""},
        "com.change_db": {"type": "counter", "unit": "", "name": u'change_db执行次数', "info": ""},

        "server.connections": {"type": "counter", "unit": "", "name": u'试图连接到MYSQL服务器的次数', "info": ""},

        "created.tmp_disk_tables": {"type": "counter", "unit": "", "name": u'磁盘上临时表的数量', "info": ""},
        "created.tmp_files": {"type": "counter", "unit": "", "name": u'临时文件的数量', "info": ""},
        "created.tmp_tables": {"type": "counter", "unit": "", "name": u'内存中临时表的数量', "info": ""},

        "innodb.buffer_pool_free": {"type": "gauge", "unit": "KB", "name": u'INNODB 缓存池的空闲大小', "info": ""},
        "innodb.buffer_pool_used": {"type": "gauge", "unit": "KB", "name": u'INNODB 缓存池的已使用大小', "info": ""},
        "innodb.buffer_pool_total": {"type": "gauge", "unit": "KB", "name": u'INNODB 缓存池的总大小', "info": ""},
        "innodb.buffer_pool_utilization": {"type": "gauge", "unit": "%", "name": u'INNODB 缓存池的使用百分比', "info": ""},

        "innodb.buffer_read_hit_rate": {"type": "gauge", "unit": "", "name": u'INNODB 缓存命中率', "info": ""},
        "innodb.data_reads": {"type": "counter", "unit": "KB", "name": u'INNODB 从文件读取的数据量', "info": ""},
        "innodb.data_writes": {"type": "counter", "unit": "KB", "name": u'INNODB 往文件写入的数据量', "info": ""},

        "innodb.os_log_fsyncs": {"type": "counter", "unit": "", "name": u'日志文件fsync操作数', "info": ""},

        "innodb.row_lock_time": {"type": "counter", "unit": "s", "name": u'行锁耗时', "info": ""},
        "innodb.row_lock_time_avg": {"type": "gauge", "unit": "s", "name": u'行锁平均耗时', "info": ""},
        "innodb.row_lock_waits": {"type": "counter", "unit": "", "name": u'行锁次数', "info": ""},

        "key.buffer_read_hit_rate": {"type": "gauge", "unit": "%", "name": u'key buffer 读命中率', "info": ""},
        "key.buffer_write_hit_rate": {"type": "gauge", "unit": "%", "name": u'key buffer 写命中率', "info": ""},

        "open.files": {"type": "gauge", "unit": "", "name": u'打开文件数', "info": ""},
        "open.tables": {"type": "gauge", "unit": "", "name": u'打开的表数量', "info": ""},

        "qcache.free_memory": {"type": "gauge", "unit": "KB", "name": u'Qcache 的空闲大小', "info": ""},
        "qcache.hits": {"type": "counter", "unit": "", "name": u'Qcache 命中次数', "info": ""},
        "qcache.inserts": {"type": "counter", "unit": "", "name": u'Qcache 插入次数', "info": ""},
        "qcache.hit_rate": {"type": "gauge", "unit": "%", "name": u'Qcache 命中率', "info": ""},

        "select.full_join": {"type": "counter", "unit": "", "name": u'full join的次数', "info": u"表扫描时执行 full join 的次数, 这些表扫描没有使用索引"},
        "select.full_range_join": {"type": "counter", "unit": "", "name": u'full range join的次数', "info": ""},
        "select.range_check": {"type": "counter", "unit": "", "name": u' range check的次数', "info": ""},

        "slow.queries": {"type": "counter", "unit": "", "name": u'慢查询数量', "info": ""},
        "server.questions": {"type": "counter", "unit": "", "name": u'SQL语句执行数量', "info": ""},

        "table.locks_immediate": {"type": "counter", "unit": "", "name": u'立即释放的表锁数量', "info": ""},
        "table.locks_waited": {"type": "counter", "unit": "", "name": u'需要等待的表锁数量', "info": ""},
        "table.open_cache_hits": {"type": "counter", "unit": "", "name": u'表高速缓存的命中次数', "info": ""},
        "table.open_cache_misses": {"type": "counter", "unit": "", "name": u'表高速缓存的未命中次数', "info": ""},
        "table.open_cache_overflows": {"type": "counter", "unit": "",
                                       "name": u'表高速缓存的溢出次数',
                                       "info": u'表高速缓存的溢出次数,每当MySQL访问一个表时，'
                                               u'如果在表缓冲区(table_open_cache)中还有空间，该表就被打开并放入其中，这样可以更快地访问表内容'
                                               u'如果 open.tables 经常大于 table_open_cache, 那么 table_open_cache 就不足了,'
                                               u'注意不要设置过大的table open cache 防止文件描述符不足'},

        "threads.connected": {"type": "gauge", "unit": "", "name": u'连接的线程数', "info": ""},
        "threads.running": {"type": "gauge", "unit": "", "name": u'running状态的线程数', "info": ""},
        "threads.cache_hit_rate": {"type": "gauge", "unit": "%", "name": u'缓存线程的命中率', "info": ""}
    }

    allow_undefined_metric = False
    conn = None
    cursor = None


    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 3306)
        config.setdefault('username', 'root')
        return config

    def create_connection(self, config):
        self.conn = pymysql.connect(
            host=config.get("host"),
            port=config.get("port"),
            user=config.get("username", ''),
            passwd=config.get("password", ''),
            connect_timeout=config.get("timeout", 5),
            charset="utf8"
        )
        self.cursor = self.conn.cursor()

    def check(self, config):
        # initialize the mysql connection
        # 注意这里检查Todo
        self.create_connection(config)

        data = {}

        # collect all mysql global status
        show_global_status = "SHOW GLOBAL STATUS;"
        self.cursor.execute(show_global_status)
        result = self.cursor.fetchall()

        for i in range(len(result)):
            key = result[i][0].lower()
            value = result[i][1]

            split_len = len(key.split("_"))
            if split_len == 1:
                corrected_key = "server." + key
            elif split_len == 2:
                corrected_key = '.'.join(key.split("_"))
            else:
                corrected_key = '.'.join(key.split("_", 1))

            data[corrected_key] = value

        # collect innodb usage
        innodb_buffer_pool_free = self._convert_to_float(data.get("innodb.buffer_pool_pages_free", 0))
        innodb_buffer_pool_total = self._convert_to_float(data.get("innodb.buffer_pool_pages_total", 0))
        innodb_buffer_pool_used = self._convert_to_float(data.get("innodb.buffer_pool_used", 0))
        innodb_page_size = self._convert_to_float(data.get("innodb.page_size", 0))
        data["innodb.buffer_pool_free"] = self._byte_convert_to_kbyte(innodb_buffer_pool_free * innodb_page_size)
        data["innodb.buffer_pool_total"] = self._byte_convert_to_kbyte(innodb_buffer_pool_total * innodb_page_size)
        data["innodb.buffer_pool_used"] = self._byte_convert_to_kbyte(innodb_buffer_pool_used * innodb_page_size)
        if innodb_buffer_pool_total == 0:
            data["innodb.buffer_pool_utilization"] = 0
        else:
            data["innodb.buffer_pool_utilization"] = \
                self._decimal_convert_to_percent(innodb_buffer_pool_free / innodb_buffer_pool_total)

        innodb_buffer_pool_reads = self._convert_to_float(data.get("innodb.buffer_pool_reads", 0))
        innodb_buffer_pool_read_requests = self._convert_to_float(data.get("innodb.buffer_pool_read_requests", 0))
        if innodb_buffer_pool_read_requests == 0:
            data["innodb.buffer_read_hit_rate"] = 0
        else:
            data["innodb.buffer_read_hit_rate"] = \
                self._decimal_convert_to_percent(1 - innodb_buffer_pool_reads / innodb_buffer_pool_read_requests)

        data["innodb.row_lock_time"] = self._millisecond_convert_to_second(data.get("innodb.row_lock_time", 0))
        data["innodb.row_lock_time_avg"] = self._millisecond_convert_to_second(data.get("innodb.row_lock_time_avg", 0))

        # collect query cache usage
        qcache_hits = self._convert_to_float(data.get("qcache.hits", 0))
        qcache_inserts = self._convert_to_float(data.get("qcache.inserts", 0))
        if (qcache_hits != 0) or (qcache_inserts != 0):
            data["qcache.hit_rate"] = self._decimal_convert_to_percent(qcache_hits / (qcache_hits + qcache_inserts))
        else:
            data["qcache.hit_rate"] = 0

        data["qcache.free_memory"] = self._byte_convert_to_kbyte(data.get("qcache.free_memory", 0))

        # collect key buffer usage
        key_reads = self._convert_to_float(data.get("key.reads", 0))
        key_read_requests = self._convert_to_float(data.get("key.read_requests", 0))
        if key_read_requests == 0:
            data["key.buffer_read_hit_rate"] = 0
        else:
            data["key.buffer_read_hit_rate"] = self._decimal_convert_to_percent(1 - key_reads / key_read_requests)

        key_writes = self._convert_to_float(data.get("key.writes", 0))
        key_write_requests = self._convert_to_float(data.get("key.write_requests", 0))
        if key_write_requests == 0:
            data["key.buffer_write_hit_rate"] = 0
        else:
            data["key.buffer_write_hit_rate"] = self._decimal_convert_to_percent(1 - key_writes / key_write_requests)

        # collect thread cache usage
        threads_created = self._convert_to_float(data.get("threads.created", 0))
        connections = self._convert_to_float(data.get("server.connections", 0))
        if connections == 0:
            data["threads.cache_hit_rate"] = 0
        else:
            data["threads.cache_hit_rate"] = self._decimal_convert_to_percent(threads_created / connections)
            
        self.clear_connection()
        return data

    def clear_connection(self):
        try:
            if self.cursor:
                self.cursor.close()

            if self.conn:
                self.conn.close()
        except:
            pass
