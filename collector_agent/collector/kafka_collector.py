#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

from collector.jvm_collector import JvmCollector


class KafkaCollector(JvmCollector):
    component = 'kafka'
    metric_define = {
        "server.bytes_out_per_sec": {"type": "gauge", "unit": "KB", "name": u"读取字节数", "info": ""},
        "server.bytes_in_per_sec": {"type": "gauge", "unit": "KB", "name": u"写入字节数", "info": ""},
        "server.messages_in_per_sec": {"type": "gauge", "unit": "", "name": u"消息写入量", "info": ""},
        "server.bytes_rejected_per_sec": {"type": "gauge", "unit": "KB", "name": u"写入失败字节数", "info": ""},

        "server.failed_fetch_requests_per_sec": {"type": "gauge", "unit": "", "name": u"读取消息失败数", "info": ""},
        "server.failed_produce_requests_per_sec": {"type": "gauge", "unit": "", "name": u"生产消息失败数", "info": ""},

        "network.request_produce_time_avg": {"type": "gauge", "unit": "ms",
                                             "name": u"生产消息的平均时间",
                                             "info": u""},
        "network.request_produce_time_99percentile": {"type": "gauge", "unit": "ms",
                                                      "name": u"生产消息平均时间的第99百分位数"
                                                              u"", "info": ""},
        "network.request_fetch_time_avg": {"type": "gauge", "unit": "ms",
                                           "name": u"消费消息的平均时间",
                                           "info": ""},
        "network.request_fetch_time_99percentile": {"type": "gauge", "unit": "ms",
                                                    "name": u"消费消息平均时间的第99百分位数",
                                                    "info": ""},

        "network.request_update_metadata_time_avg": {"type": "gauge", "unit": "ms",
                                                     "name": u"更新元数据的平均时间", "info": ""},
        "network.request_update_metadata_time_99percentile": {"type": "gauge", "unit": "ms",
                                                              "name": u"更新元数据平均时间的第99百分位数",
                                                              "info": ""},

        "network.request_metadata_time_avg": {"type": "gauge", "unit": "ms",
                                              "name": u"获取元数据的平均时间",
                                              "info": ""},
        "network.request_metadata_time_99percentile": {"type": "gauge", "unit": "ms",
                                                       "name": u"获取元数据平均时间的第99百分位数",
                                                       "info": ""},

        "network.request_offsets_time_avg": {"type": "gauge", "unit": "ms",
                                             "name": u"获取offset的平均时间",
                                             "info": ""},
        "network.request_offsets_time_99percentile": {"type": "gauge", "unit": "ms",
                                                      "name": u"获取offset平均时间的第99百分位数",
                                                      "info": ""},

        "server.request_handler_avg_idle_percent": {"type": "gauge", "unit": "%", "name": u"请求线程的时间空闲率", "info": ""},

        "server.replication_isr_shrinks": {"type": "gauge", "unit": "",
                                           "name": u"ISR的收缩速率",
                                           "info": u"如果一个broker挂掉了，一些partition的ISR会收缩;当那个broker重新起来时，一旦它的replica完全跟上，ISR会扩大(expand);除此之外，正常情况下，此值和扩大速率都是0."},
        "server.replication_isr_expands": {"type": "gauge", "unit": "",
                                           "name": u"ISR的扩大速率",
                                           "info": u"如果一个broker挂掉了，一些partition的ISR会收缩;当那个broker重新起来时，一旦它的replica完全跟上，ISR会扩大(expand);除此之外，正常情况下，此值和收缩速率都是0."},

        "controller.replication_leader_elections": {"type": "gauge", "unit": "",
                                                    "name": u"Leader的选举速率", "info": u"当此值非0时, 有Broker失效"},
        "controller.replication_unclean_leader_elections": {"type": "gauge", "unit": "",
                                                            "name": u"Unclean的leader选举速率", "info": ""},

        "log.flush_rate": {"type": "gauge", "unit": "", "name": u"日志Flush的速率", "info": ""}

    }

    metric_define.update(JvmCollector.metric_define)
    allow_undefined_metric = False

    def check(self, config):
        data = {}

        data = super(KafkaCollector, self).check(config)

        # data process
        if data:
            data["server.bytes_out_per_sec"] = self._byte_convert_to_kbyte(data.get("server.bytes_out_per_sec", 0.0))
            data["server.bytes_in_per_sec"] = self._byte_convert_to_kbyte(data.get("server.bytes_in_per_sec", 0.0))
            data["server.bytes_rejected_per_sec"] = self._byte_convert_to_kbyte(
                    data.get("server.bytes_rejected_per_sec", 0.0)
            )

        return data

