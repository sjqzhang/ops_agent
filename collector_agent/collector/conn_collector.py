#!/usr/local/easyops/python/bin/python
#-*- coding: utf-8 -*-
import os
import time
import json

import psutil

from collector.easy_collector import EasyCollector


class ConnCollector(EasyCollector):
    """废弃"""
    component = 'conn'
    data_id = 8006
    metric_define = {
        'connections': {"type": "text", "unit": "", "name": u"长连接数据", "info": ""},
    }

    def check(self, config):
        res = {}
        res['connections'] = json.dumps(self.get_connections())
        return res

    def get_instances(self):
        return [{}]

    def fill_default_config(self, config):
        return config

    def get_connections(self):
        listening = []
        connections = psutil.net_connections()
        for conn in connections:
            if not conn.pid:
                continue
            if conn.status == psutil.CONN_LISTEN:
                ip, port = conn.laddr
                # instance = '%s:%s' % (ip, port)
                if port not in listening:
                    listening.append(port)

        res = []
        clients = {}
        for conn in connections:
            if not conn.pid:
                continue
            if not conn.status == psutil.CONN_ESTABLISHED:
                continue

            ip, port = conn.laddr
            # instance = '%s:%s' % (ip, port)
            if port in listening:
                continue

            try:
                proc = psutil.Process(conn.pid)
            except psutil.NoSuchProcess:
                continue

            current = time.time()
            create_time = proc.create_time()
            if current - create_time < 60 * 5:
                continue

            rip, rport = conn.raddr
            record_id = '%s-%s:%s' % (conn.pid, rip, rport)
            client = clients.setdefault(record_id, {})
            if not client:
                client['client_pid'] = conn.pid
                client['client_process_create_time'] = int(create_time)
                client['client_pname'] = proc.name()
                client['client_cwd'] = proc.cwd()
                client['client_ip'] = ip
                # client['client_ports'] = '%s' % port
                client['client_port_num'] = 1
                client['server_ip'] = rip
                client['server_port'] = rport
                client['server_pid'] = ''
                client['server_pname'] = ''
            else:
                # client['client_ports'] += ', %s' % port
                client['client_port_num'] += 1

        res = clients.values()
        res.sort(key=lambda x: (x['client_pid'], x['server_port']))
        return res


if __name__ == '__main__':
    coll = ConnCollector()
    print json.dumps(coll.get_connections(), indent=4, sort_keys=True)
