#-*- coding: utf-8 -*-
__author__ = 'hzp'
import json
import psutil
import sys
import random
import time

from collector.easy_collector import EasyCollector
import topo.packet_sniffer.pcap_packet_sniff
import gevent
import operator
from netifaces import interfaces, ifaddresses, AF_INET


class SniffSide(object):
    """
    抓包方
    """
    Client = "c"
    Server = "s"


class TopoCollector(EasyCollector):
    data_id = 1301
    max_text_length = sys.maxint
    DETECT_TIME = 10.0

    component = 'topo'
    metric_define = {
        'topo': {"type": "text", "unit": "", "name": u'topo', "info": "topo"},
        'type': {"type": "text", "unit": "", "name": u'type', "info": "type"}
    }

    check_timeout = 100000

    def plugin_init(self):
        ret, msg = EasyCollector.plugin_init(self)
        if ret != 0:
            return ret, msg
        self._iplist = self._ip4_addresses()
        return ret, msg

    def check(self, config):
        if not self._can_sniff():
            return {"topo": json.dumps([]), "type": "host"}

        self._random_sleep(self.config["random_sleep"])

        sniffer = topo.packet_sniffer.pcap_packet_sniff.PcapPacketSniff(self.logger)
        links = sniffer.sniff(self.config["packet_count"], self.config["sniff_timeout"])
        if links is None:
            return {"topo": json.dumps([]), "type": "host", "error": "sniff error!"}

        listen_ports = self.get_listen_ports()
        pcap_links = self._merge_links(links, listen_ports)
        res = {"topo": json.dumps(pcap_links), "type": "host"}
        self.logger.debug("report topo: {}".format(res))
        return res

    def _merge_links(self, links, listen_ports):
        stat = {}
        self.logger.info("listen ports: {}".format(listen_ports))
        self.logger.info("iplist: {}".format(self._iplist))
        cnt = 0
        for link in links:
            if cnt % 1000 == 0:
                time.sleep(1)
            cnt += 1
            micro_ts, packet_type, src_ip, src_port, dst_ip, dst_port, length, syn = link

            # 过滤空包
            if length == 0:
                continue

            if self._in_listen_ports(src_port, listen_ports) and src_ip in self._iplist:
                client_ip = dst_ip
                server_ip = src_ip
                server_port = src_port
                sniff_side = SniffSide.Server
            elif self._in_listen_ports(dst_port, listen_ports) and dst_ip in self._iplist:
                client_ip = src_ip
                server_ip = dst_ip
                server_port = dst_port
                sniff_side = SniffSide.Server
            elif not self._in_listen_ports(src_port, listen_ports) and src_ip in self._iplist:
                client_ip = src_ip
                server_ip = dst_ip
                server_port = dst_port
                sniff_side = SniffSide.Client
            elif not self._in_listen_ports(dst_port, listen_ports) and dst_ip in self._iplist:
                client_ip = dst_ip
                server_ip = src_ip
                server_port = src_port
                sniff_side = SniffSide.Client
            else:
                self.logger.info("not in listen ports: {}, {}, {}, {}".format(src_ip, src_port, dst_ip, dst_port))
                continue

            if (client_ip, server_ip, server_port) not in stat:
                stat[(client_ip, server_ip, server_port)] = {"length": 0, "count": 0}
            stat[(client_ip, server_ip, server_port)]["length"] += length
            stat[(client_ip, server_ip, server_port)]["count"] += 1
            stat[(client_ip, server_ip, server_port)]["sniff_side"] = sniff_side

        merge_results = []
        cnt = 0
        for (client_ip, server_ip, server_port), stat_info in stat.iteritems():
            if cnt % 1000 == 0:
                time.sleep(1)
            cnt += 1
            merge_results.append(
                {
                    "cip": client_ip,
                    "sip": server_ip,
                    "sport": server_port,
                    "len": stat_info["length"],
                    "count": stat_info["count"],
                    "sniff_side": stat_info["sniff_side"]
                }
            )
        # 挑交互次数最多的上报。
        if len(merge_results) > self.config["max_report"]:
            merge_results.sort(key=operator.itemgetter('count'), reverse=True)

        return merge_results[:self.config["max_report"]]

    def _can_sniff(self):
        cpu_usage = psutil.cpu_percent(TopoCollector.DETECT_TIME)
        self.logger.info("cpu_usage: {}".format(cpu_usage))
        if cpu_usage > self.config["cpu_threshold"]:
            self.logger.info("cpu_usage overload: {}".format(cpu_usage))
            return False

        stat0 = psutil.net_io_counters(pernic=True)
        gevent.sleep(TopoCollector.DETECT_TIME)
        stat1 = psutil.net_io_counters(pernic=True)
        for eth_name, stat0_eth_stat in stat0.iteritems():
            if eth_name == "lo":
                continue

            stat1_eth_stat = stat1.get(eth_name)
            if stat1_eth_stat is None:
                continue

            packets_sent = (stat1_eth_stat.packets_sent - stat0_eth_stat.packets_sent) / TopoCollector.DETECT_TIME
            self.logger.info("packets_sent: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.packets_sent, stat0_eth_stat.packets_sent, packets_sent))
            if packets_sent > self.config["packets_threshold"]:
                self.logger.info("packets_sent overload: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.packets_sent, stat0_eth_stat.packets_sent, packets_sent))
                return False

            packets_recv = (stat1_eth_stat.packets_recv - stat0_eth_stat.packets_recv) / TopoCollector.DETECT_TIME
            self.logger.info("packets_recv: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.packets_recv, stat0_eth_stat.packets_recv, packets_recv))
            if packets_recv > self.config["packets_threshold"]:
                self.logger.info("packets_recv overload: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.packets_recv, stat0_eth_stat.packets_recv, packets_recv))
                return False

            mbits_sent = (stat1_eth_stat.bytes_sent - stat0_eth_stat.bytes_sent) / TopoCollector.DETECT_TIME / 1024 / 1024 * 8
            self.logger.info("mbits_sent: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.bytes_sent, stat0_eth_stat.bytes_sent, mbits_sent))
            if mbits_sent > self.config["net_flow_threshold"]:
                self.logger.info("net flow overload: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.bytes_sent, stat0_eth_stat.bytes_sent, mbits_sent))
                return False

            mbits_recv = (stat1_eth_stat.bytes_recv - stat0_eth_stat.bytes_recv) / TopoCollector.DETECT_TIME / 1024 / 1024 * 8
            self.logger.info("mbits_recv: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.bytes_recv, stat0_eth_stat.bytes_recv, mbits_recv))
            if mbits_recv > self.config["net_flow_threshold"]:
                self.logger.info("net flow overload: {}, {}, {}, {}".format(eth_name, stat1_eth_stat.bytes_recv, stat0_eth_stat.bytes_recv, mbits_recv))
                return False

        return True

    def get_instances(self):
        return [{}]

    def get_listen_ports(self):
        """
        获取监听端口
        :return: 监听端口列表
        """
        listen_ports = []
        connections = psutil.net_connections()
        for connection in connections:
            if connection.status == "LISTEN":
                listen_ports.append((connection.laddr[1], connection.pid))
        return listen_ports

    def _in_listen_ports(self, port, listen_ports):
        for (listen_port, _) in listen_ports:
            if port == listen_port:
                return True
        return False

    def _ip4_addresses(self):
        ip_list = []
        try:
            for interface in interfaces():
                if AF_INET not in ifaddresses(interface):
                    continue
                for link in ifaddresses(interface)[AF_INET]:
                    if 'addr' not in link:
                        continue
                    ip_list.append(link['addr'])
        except Exception, e:
            self.logger.error("get ip address fail: e={}".format(e))
            return []
        return ip_list

    def _random_sleep(self, seconds):
        rand_seconds = random.randint(0, seconds)
        self.logger.info("random sleep start: {}".format(rand_seconds))
        gevent.sleep(rand_seconds)
        self.logger.info("random sleep finish: {}".format(rand_seconds))
