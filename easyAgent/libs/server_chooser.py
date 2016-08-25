# -*- coding: utf-8 -*-
__author__ = 'hzp'
import random


class ServerChooser:
    """
    server选择
    """

    @staticmethod
    def choose_server(server_list):
        """
        按策略选择出server
        :param server_list: [ip:port, ip:port]
        :return: None为找不到， 否则返回字符串ip:port
        """
        if len(server_list) == 0:
            return None
        idx = random.randint(0, 57643673)
        return server_list[idx % len(server_list)]
