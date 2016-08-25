#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
import psutil
import gevent
from collections import Counter

from utils.ip_util import ip_to_int
from collector.easy_collector import EasyCollector


class NetworkCollector(EasyCollector):
    component = 'host'
    metric_define = {
        'net.bits_in': {"type": "counter", "unit": "kbps", "name": u'网络接收流量', "info": u"总接收比特，包括lo"},
        'net.bits_out': {"type": "counter", "unit": "kbps", "name": u'网络发送流量', "info": u"总发送比特率，包括lo"},
        'net.packages_in': {"type": "counter", "unit": "pps", "name": u'网络接收包量', "info": u"总接收包率，包括lo"},
        'net.packages_out': {"type": "counter", "unit": "pps", "name": u'网络发送包量', "info": u"总发送包率，包括lo"},
        'net.error_in': {"type": "counter", "unit": "", "name": u'网络接收错误包量', "info": u"总接收错误包量"},
        'net.error_out': {"type": "counter", "unit": "", "name": u'网络发送错误包量', "info": u"总发送错误包量"},
        'net.drop_in': {"type": "counter", "unit": "", "name": u'网络接收丢包量', "info": u"总接收丢包量"},
        'net.drop_out': {"type": "counter", "unit": "", "name": u'网络发送丢包量', "info": u"总发送丢包量"},
        'net.avg_package_in_size': {"type": "gauge", "unit": "byte", "name": u'平均接收包大小', "info": u"平均接收包大小，正常应该在512byte左右"},
        'net.avg_package_out_size': {"type": "gauge", "unit": "byte", "name": u'平均发送包大小', "info": u"平均发送包大小，正常应该在512byte左右"},

        # 区分内外网流量
        'net.inner_bits_in': {"type": "counter", "unit": "kbps", "name": u'内网接收流量', "info": ""},
        'net.inner_bits_out': {"type": "counter", "unit": "kbps", "name": u'内网发送流量', "info": ""},
        'net.inner_packages_in': {"type": "counter", "unit": "pps", "name": u'内网接收包量', "info": ""},
        'net.inner_packages_out': {"type": "counter", "unit": "pps", "name": u'内网发送包量', "info": ""},
        # 'net.inner_error_in': {"type": "counter", "unit": "", "name": u'内网接收总错误包量', "info": ""},
        # 'net.inner_error_out': {"type": "counter", "unit": "", "name": u'内网发送错误包量', "info": ""},
        # 'net.inner_drop_in': {"type": "counter", "unit": "", "name": u'内网接收总丢包量', "info": ""},
        # 'net.inner_drop_out': {"type": "counter", "unit": "", "name": u'内网发送总丢包量', "info": ""},

        'net.outer_bits_in': {"type": "counter", "unit": "kbps", "name": u'外网接收流量', "info": ""},
        'net.outer_bits_out': {"type": "counter", "unit": "kbps", "name": u'外网发送流量', "info": ""},
        'net.outer_packages_in': {"type": "counter", "unit": "pps", "name": u'外网接收包量', "info": ""},
        'net.outer_packages_out': {"type": "counter", "unit": "pps", "name": u'外网发送包量', "info": ""},
        # 'net.outer_error_in': {"type": "counter", "unit": "", "name": u'外网接收总错误包量', "info": ""},
        # 'net.outer_error_out': {"type": "counter", "unit": "", "name": u'外网发送错误包量', "info": ""},
        # 'net.outer_drop_in': {"type": "counter", "unit": "", "name": u'外网接收总丢包量', "info": ""},
        # 'net.outer_drop_out': {"type": "counter", "unit": "", "name": u'外网发送总丢包量', "info": ""},

        # 'net.lo_bits_in': {"type": "counter", "unit": "kbit", "name": u'环路接收总bit数', "info": ""},
        # 'net.lo_bits_out': {"type": "counter", "unit": "kbit", "name": u'环路发送总bit数', "info": ""},
        # 'net.lo_packages_in': {"type": "counter", "unit": "", "name": u'环路接收总包量', "info": ""},
        # 'net.lo_packages_out': {"type": "counter", "unit": "", "name": u'环路发送总包量', "info": ""},
        # 'net.lo_error_in': {"type": "counter", "unit": "", "name": u'环路接收总错误包量', "info": ""},
        # 'net.lo_error_out': {"type": "counter", "unit": "", "name": u'环路发送错误包量', "info": ""},
        # 'net.lo_drop_in': {"type": "counter", "unit": "", "name": u'环路接收总丢包量', "info": ""},
        # 'net.lo_drop_out': {"type": "counter", "unit": "", "name": u'环路发送总丢包量', "info": ""},

        'net.conn_established': {"type": "gauge", "unit": "", "name": u'已建立连接数', "info": ""},
        'net.conn_syn_sent': {"type": "gauge", "unit": "", "name": u'SYN SENT连接数', "info": ""},
        'net.conn_syn_recv': {"type": "gauge", "unit": "", "name": u'SYN RECV连接数', "info": u"SYN RECV连接数，如果太大，可能是被SYN攻击"},
        'net.conn_fin_wait1': {"type": "gauge", "unit": "", "name": u'FIN WAIT1连接数', "info": ""},
        'net.conn_fin_wait2': {"type": "gauge", "unit": "", "name": u'FIN WAIT2连接数', "info": ""},
        'net.conn_time_wait': {"type": "gauge", "unit": "", "name": u'TIME WAIT连接数', "info": u"TIME WAIT连接数，如果太大，需调节TCP连接参数"},
        'net.conn_listen': {"type": "gauge", "unit": "", "name": u'LISTEN连接数', "info": ""},
        # 'net.conn_close': {"type": "gauge", "unit": "", "name": u'CLOSE连接数', "info": ""},
        # 'net.conn_close_wait': {"type": "gauge", "unit": "", "name": u'CLOSE WAIT连接数', "info": ""},
        # 'net.conn_last_ack': {"type": "gauge", "unit": "", "name": u'LAST ACK连接数', "info": ""},
        # 'net.conn_closing': {"type": "gauge", "unit": "", "name": u'CLOSING连接数', "info": ""},
        'net.conn_total': {"type": "gauge", "unit": "", "name": u'总连接数', "info": ""},

        'net.max_conn_by_raddr': {"type": "gauge", "unit": "", "name": u'单个IP最大连接数', "info": ""},
        'net.max_conn_raddr': {"type": "text", "unit": "", "name": u'连接数最多的IP', "info": u"连接数最多的IP，如果太多，可能是一个非法连接"},

        'net.max_conn_by_lport': {"type": "gauge", "unit": "", "name": u'单个端口最大连接数', "info": ""},
        'net.max_conn_lport': {"type": "text", "unit": "", "name": u'连接数最多的端口', "info": u"连接数最多的端口，这个可以标志提供的服务"},

    }
    allow_undefined_metric = True

    def __init__(self, *args, **kwargs):
        super(NetworkCollector, self).__init__(*args, **kwargs)
        self.inner_ips = {
            24: ip_to_int('10.255.255.255') >> 24,
            20: ip_to_int('172.31.255.255') >> 20,
            16: ip_to_int('192.168.255.255') >> 16
        }

    def _get_eth_info(self):
        eth_info = {
            'inner': [],
            'outer': [],
            'lo': []
        }
        info = psutil.net_if_addrs()
        for eth, net in info.iteritems():
            ip = None
            for n in net:
                if n.family == 2 and n.address:
                    ip = n.address
                    break
            else:
                continue
            if ip is None:
                continue
            ip_type = self._get_ip_type(ip)
            eth_info[ip_type].append(eth)
        return eth_info

    def _is_inner_ip(self, ip):
        ip_int = ip_to_int(ip)
        for bit, val in self.inner_ips.iteritems():
            if (ip_int >> bit) == val:
                return True
        return False

    def _get_ip_type(self, ip):
        if self._is_inner_ip(ip):
            return 'inner'
        elif ip in ('127.0.0.1',):
            return 'lo'
        else:
            return 'outer'

    def check(self):
        data = {k: 0 for k in self.metric_define}
        eth_info = self._get_eth_info()
        stat = psutil.net_io_counters(pernic=True)
        for eth_type, eth_names in eth_info.iteritems():
            for eth_name in eth_names:
                # 2016-06-13，由于bond网卡的原因，导致这里会有问题，临时解决。todo
                if eth_name not in stat:
                    continue
                data['net.bits_in'] += stat[eth_name].bytes_recv / 1024 * 8 #kbit
                data['net.bits_out'] += stat[eth_name].bytes_sent / 1024 * 8
                data['net.packages_in'] += stat[eth_name].packets_recv
                data['net.packages_out'] += stat[eth_name].packets_sent
                data['net.error_in'] += stat[eth_name].errin
                data['net.error_out'] += stat[eth_name].errout
                data['net.drop_in'] += stat[eth_name].dropin
                data['net.drop_out'] += stat[eth_name].dropout
                if eth_type == 'lo':
                    continue
                data['net.{0}_bits_in'.format(eth_type)] += stat[eth_name].bytes_recv / 1024 * 8
                data['net.{0}_bits_out'.format(eth_type)] += stat[eth_name].bytes_sent / 1024 * 8
                data['net.{0}_packages_in'.format(eth_type)] += stat[eth_name].packets_recv
                data['net.{0}_packages_out'.format(eth_type)] += stat[eth_name].packets_sent
                # data['net.{0}_error_in'.format(eth_type)] += stat[eth_name].errin
                # data['net.{0}_error_out'.format(eth_type)] += stat[eth_name].errout
                # data['net.{0}_drop_in'.format(eth_type)] += stat[eth_name].dropin
                # data['net.{0}_drop_out'.format(eth_type)] += stat[eth_name].dropout
        # data['net.avg_package_out_size'] = (data['net.bits_out'] / 8 * 1000 / data['net.packages_out']) if data['net.packages_out'] else 0
        # data['net.avg_package_in_size'] = (data['net.bits_in'] / 8 * 1000 / data['net.packages_in']) if data['net.packages_in'] else 0
        gevent.sleep()
        stat = psutil.net_connections()
        conn_by_raddr = {}
        conn_by_lport = {}
        for conn in stat:
            key = 'net.conn_%s' %conn.status.lower()
            if key not in data:
                continue
            data[key] += 1
            # 按目标IP统计连接数
            if conn.raddr:
                raddr = conn.raddr[0]
                conn_by_raddr.setdefault(raddr, 0)
                conn_by_raddr[raddr] += 1
            # 按本地端口统计连接数
            if conn.laddr:
                lport = conn.laddr[1]
                conn_by_lport.setdefault(lport, 0)
                conn_by_lport[lport] += 1

        data['net.conn_total'] = len(stat)
        max_conn_by_raddr = Counter(conn_by_raddr).most_common(1)
        if max_conn_by_raddr:
            data['net.max_conn_by_raddr'] = max_conn_by_raddr[0][1]
            data['net.max_conn_raddr'] = max_conn_by_raddr[0][0]
        else:
            data['net.max_conn_by_raddr'] = 0
            data['net.max_conn_raddr'] = ''
        max_conn_by_lport = Counter(conn_by_lport).most_common(1)
        if max_conn_by_lport:
            data['net.max_conn_by_lport'] = max_conn_by_lport[0][1]
            data['net.max_conn_lport'] = max_conn_by_lport[0][0]
        else:
            data['net.max_conn_by_lport'] = 0
            data['net.max_conn_lport'] = ''
        return data


    def shape_all_values(self, data):
        # 平均包大小应该是统计时间间隔内包的流量/包的数量
        data['host.net.avg_package_out_size'] = (data['host.net.bits_out'] / 8 * 1000 / data['host.net.packages_out']) if data.get('host.net.packages_out') else 0
        data['host.net.avg_package_in_size'] = (data['host.net.bits_in'] / 8 * 1000 / data['host.net.packages_in']) if data.get('host.net.packages_in') else 0
        #计算比特率和包率
        if data.get('host.net.bits_in'):
            # 平均包大小应该是统计时间间隔内包的流量/包的数量
            data['host.net.avg_package_out_size'] = (data['host.net.bits_out'] / 8 * 1000 / data['host.net.packages_out']) if data.get('host.net.packages_out') else 0
            data['host.net.avg_package_in_size'] = (data['host.net.bits_in'] / 8 * 1000 / data['host.net.packages_in']) if data.get('host.net.packages_in') else 0
            #计算比特率和包率
            data['host.net.bits_in'] = data['host.net.bits_in'] / 60
            data['host.net.bits_out'] = data['host.net.bits_out'] / 60
            data['host.net.packages_in'] = data['host.net.packages_in'] / 60
            data['host.net.packages_out'] = data['host.net.packages_out'] / 60

            data['host.net.inner_bits_in'] = data['host.net.inner_bits_in'] / 60
            data['host.net.inner_bits_out'] = data['host.net.inner_bits_out'] / 60
            data['host.net.inner_packages_in'] = data['host.net.inner_packages_in'] / 60
            data['host.net.inner_packages_out'] = data['host.net.inner_packages_out'] / 60

            data['host.net.outer_bits_in'] = data['host.net.outer_bits_in'] / 60
            data['host.net.outer_bits_out'] = data['host.net.outer_bits_out'] / 60
            data['host.net.outer_packages_in'] = data['host.net.outer_packages_in'] / 60
            data['host.net.outer_packages_out'] = data['host.net.outer_packages_out'] / 60
        return data
