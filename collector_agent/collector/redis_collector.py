#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import redis

from collector.easy_collector import EasyCollector


class RedisCollector(EasyCollector):
    component = 'redis'
    metric_define = {
        "clients.blocked_clients": {"type": "gauge", "unit": "",
                                    "name": u'阻塞客户端数量', "info": u"正在等待阻塞命令（BLPOP、BRPOP、BRPOPLPUSH）的客户端的数量"},
        "clients.connected_clients": {"type": "gauge", "unit": "", "name": u'连接客户端数量', "info": u"不包括通过从属服务器连接的客户端"},
        "clients.connected_clients_pct": {"type": "gauge", "unit": "", "name": u'客户端连接成功率', "info": ""},
        "clients.client_biggest_input_buf": {"type": "gauge", "unit": "", "name": u'当前客户端中最大输入缓存', "info": ""},
        "clients.client_longest_output_list": {"type": "gauge", "unit": "", "name": u'当前客户端中最长的输出列表', "info": ""},

        "memory.used_memory": {"type": "gauge", "unit": "KB", "name": u'内存使用量', "info": ""},
        "memory.used_memory_peak": {"type": "gauge", "unit": "KB", "name": u"内存使用峰值", "info": ""},
        "memory.used_memory_rss": {"type": "gauge", "unit": "KB", "name": u"操作系统看到的内存使用量",
                                                                  "info": u'从操作系统的角度, '
                                                                          u'返回 Redis 已分配的内存总量(俗称常驻集大小). '
                                                                          u'这个值和 top\ps 等命令的输出一致, '
                                                                          u'以 KB 为单位'},
        "memory.used_memory_lua": {"type": "gauge", "unit": "KB", "name": u'Lua内存使用量', "info": ""},
        "memory.used_memory_pct": {"type": "gauge", "unit": "%", "name": u'内存使用率', "info": ""},
        "memory.mem_fragmentation_ratio": {"type": "gauge", "unit": "%",
                                           "name": u'内存碎片率', "info": u"通过 used_memory_rss / used_memory 可得"},

        "persistence.rdb_changes_since_last_save": {"type": "gauge", "unit": "s",
                                                    "name": u'距离上次rdb时间', "info": ""},
        "persistence.rdb_last_bgsave_time_sec": {"type": "gauge", "unit": "s",
                                                 "name": u'最近rdb用时', "info": ""},
        "persistence.rdb_current_bgsave_time_sec": {"type": "gauge", "unit": "s",
                                                    "name": u'当前rdb操作用时', "info": ""},
        "persistence.aof_last_rewrite_time_sec": {"type": "gauge", "unit": "s",
                                                  "name": u'最近创建AOF文件用时', "info": ""},
        "persistence.aof_current_rewrite_time_sec": {"type": "gauge", "unit": "s",
                                                     "name": u'当前AOF操作用时', "info": ""},

        "stats.total_connections_received": {"type": "counter", "unit": "", "name": u'总连接数', "info": ""},
        "stats.total_commands_processed": {"type": "counter", "unit": "", "name": u'执行命令数', "info": ""},
        "stats.instantaneous_ops_per_sec": {"type": "gauge", "unit": "", "name": u'每秒执行命令数', "info": ""},
        "stats.rejected_connections": {"type": "counter", "unit": "", "name": u'拒绝连接数', "info": u"因为最大客户端数量限制而被拒绝的连接请求数量"},

        "stats.expired_keys": {"type": "counter", "unit": "", "name": u'过期key数量', "info": u"因为过期而被自动删除的数据库键数量"},
        "stats.evicted_keys": {"type": "counter", "unit": "", "name": u'剔除key数量', "info": u"因为最大内存容量限制而被剔除（evict）的键数量"},
        "stats.keyspace_hits": {"type": "counter", "unit": "", "name": u'查找key成功数', "info": ""},
        "stats.keyspace_misses": {"type": "counter", "unit": "", "name": u'查找key失败数', "info": ""},

        "stats.pubsub_channels": {"type": "gauge", "unit": "", "name": u'目前被订阅的频道数量', "info": ""},
        "stats.pubsub_patterns": {"type": "gauge", "unit": "", "name": u'目前被订阅的模式数量', "info": ""},
        "stats.latest_fork_usec": {"type": "gauge", "unit": "s", "name": u'上次fork操作用时', "info": ""},

        "stats.total_net_input_bytes": {"type": "counter", "unit": "KB", "name": u'接收总数据量', "info": ""},
        "stats.total_net_output_bytes": {"type": "counter", "unit": "KB", "name": u'发送总数据量', "info": ""},

        "stats.sync_full": {"type": "gauge", "unit": "", "name": u'主从全复制次数', "info": ""},
        "stats.sync_partial_err": {"type": "gauge", "unit": "", "name": u'主从部分复制产生的错误次数', "info": ""},
        "stats.sync_partial_ok": {"type": "gauge", "unit": "", "name": u'主从部分复制产生的成功次数', "info": ""},
        "stats.migrate_cached_sockets": {"type": "gauge", "unit": "", "name": u'MIGRATE缓存的套接字数量', "info": ""},

        # "replication.role": {"type": "gauge", "unit": "", "name": u'服务器主从角色', "info": ""},
        "replication.connected_slaves": {"type": "gauge", "unit": "", "name": u'已连接的从服务器数量', "info": ""},

        # UNKNOWN FOR NOW
        "replication.master_repl_offset": {"type": "gauge", "unit": "", "name": u'replication.master_repl_offset', "info": ""},
        "replication.repl_backlog_active": {"type": "gauge", "unit": "", "name": u'replication.repl_backlog_active', "info": ""},
        "replication.repl_backlog_size": {"type": "gauge", "unit": "", "name": u'replication.repl_backlog_size', "info": ""},
        "replication.repl_backlog_first_byte_offset": {"type": "gauge", "unit": "", "name": u'replication.repl_backlog_first_byte_offset', "info": ""},
        "replication.repl_backlog_histlen": {"type": "gauge", "unit": "", "name": u'replication.repl_backlog_histlen', "info": ""},

        "cpu.used_cpu_sys": {"type": "counter", "unit": "%", "name": u'redis服务器内核态CPU时间', "info": ""},
        "cpu.used_cpu_user": {"type": "counter", "unit": "%", "name": u'redis服务器用户态CPU时间', "info": ""},
        "cpu.used_cpu_sys_children": {"type": "counter", "unit": "%", "name": u'后台进程内核态CPU时间', "info": ""},
        "cpu.used_cpu_user_children": {"type": "counter", "unit": "%", "name": u'后台进程用户态CPU时间', "info": ""},

    }

    allow_undefined_metric = False 

    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 6379)
        config.setdefault('timeout', 5)
        return config

    def check(self, config):
        data = {}

        if config.get('password'):
            redis_cli = redis.StrictRedis(
                host=config.get('host'),
                port=config.get('port'),
                password=config.get('password'),
                socket_timeout=config.get("timeout", config['timeout'])
            )
        else:
            redis_cli = redis.StrictRedis(
                host=config.get('host'),
                port=config.get('port'),
                socket_timeout=config.get("timeout", config['timeout'])
            )                

        redis_info_sections = ("server", "clients", "memory", "persistence", "stats", "replication", "cpu", "cluster")

        # 整体采集
        for count in range(len(redis_info_sections)):
            redis_info = redis_cli.info(redis_info_sections[count])

            for key in redis_info.keys():
                corrected_key = redis_info_sections[count] + "." + key
                data[corrected_key] = redis_info[key]

        # data process - clients
        redis_maxclients = redis_cli.execute_command("config get maxclients")[1]
        if float(redis_maxclients) == 0:
            data['clients.connected_clients_pct'] = 0
        else:
            data['clients.connected_clients_pct'] = \
                self._convert_to_float(data.get("clients.connected_clients", 0)) / float(redis_maxclients) * 100

        # data process - memory
        redis_maxmemory = redis_cli.execute_command("config get maxmemory")[1]
        data["memory.used_memory"] = self._byte_convert_to_kbyte(data.get("memory.used_memory", 0))
        data["memory.used_memory_peak"] = self._byte_convert_to_kbyte(data.get("memory.used_memory_peak", 0))
        data["memory.used_memory_rss"] = self._byte_convert_to_kbyte(data.get("memory.used_memory_rss", 0))
        data["memory.used_memory_lua"] = self._byte_convert_to_kbyte(data.get("memory.used_memory_lua", 0))
        data["memory.mem_fragmentation_ratio"] = \
            self._decimal_convert_to_percent(data.get("memory.mem_fragmentation_ratio", 0))
        if float(redis_maxmemory) == 0:
            data['memory.used_memory_pct'] = 0
        else:
            data['memory.used_memory_pct'] = data["memory.used_memory"] * 100 / float(redis_maxmemory)

        # # 数据加工 replication
        # if data["replication." + "role"] == "master":
        #     data["replication." + "role"] = 0
        # else:
        #     data["replication." + "role"] = 1

        data["stats.latest_fork_usec"] = self._millisecond_convert_to_second(data.get("stats.latest_fork_usec", 0))

        # data process - network
        data["stats.total_net_input_bytes"] = self._byte_convert_to_kbyte(data.get("stats.total_net_input_bytes", 0))
        data["stats.total_net_output_bytes"] = self._byte_convert_to_kbyte(data.get("stats.total_net_output_bytes", 0))

        return data
