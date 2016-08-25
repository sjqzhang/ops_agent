#-*- coding: utf-8 -*-
__author__ = 'hzp'


class PacketSniff(object):
    def __init__(self, logger):
        self._logger = logger

    def sniff(self, count, timeout):
        """
        抓包方法
        :param count: 抓包数量
        :param timeout: 抓包时间
        :return: [(nano_ts, type(tcp or udp), src_ip, src_port, dst_ip, dst_port, length, syn), ...]
        """
        return []

