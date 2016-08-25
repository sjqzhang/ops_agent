#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import json
from collector.easy_collector import EasyCollector
from libs.http_util import do_http


class StormTopologyCollector(EasyCollector):
    component = 'storm_topology'

    metric_define = {
        "topology.id": {"type": "text", "unit": "", "name": u'拓扑id', "info": "", "field_type": "dim"},
        "topology.uptime": {"type": "text", "unit": "", "name": u'拓扑Uptime', "info": ""},
        "topology.status": {"type": "text", "unit": "", "name": u'拓扑状态', "info": ""},
        "node.id": {"type": "text", "unit": "", "name": u'节点id', "info": "", "field_type": "dim"},
        "node.type": {"type": "text", "unit": "", "name": u'节点类型', "info": "", "field_type": "dim"},
        "node.executors": {"type": "gauge", "unit": "", "name": u'Executors', "info": ""},
        "node.tasks": {"type": "gauge", "unit": "", "name": u'Tasks', "info": ""},
        "node.emitted": {"type": "counter", "unit": "", "name": u'Emitted', "info": ""},
        "node.transferred": {"type": "counter", "unit": "", "name": u'Transferred', "info": ""},
        "node.capacity": {"type": "gauge", "unit": "", "name": u'Capacity', "info": ""},
        "node.completeLatency": {"type": "gauge", "unit": "ms", "name": u'Complete latency', "info": ""},
        "node.executeLatency": {"type": "gauge", "unit": "ms", "name": u'Execute latency', "info": ""},
        "node.processLatency": {"type": "gauge", "unit": "ms", "name": u'Process latency', "info": ""},
        "node.acked": {"type": "counter", "unit": "", "name": u'Acked', "info": u""},
        "node.failed": {"type": "counter", "unit": "", "name": u'Failed', "info": u""},
        "node.errorHost": {"type": "text", "unit": "", "name": u'Error Host', "info": ""},
        "node.errorPort": {"type": "text", "unit": "", "name": u'Error Port', "info": ""},
        "node.lastError": {"type": "text", "unit": "", "name": u'Last error', "info": ""},
    }

    allow_undefined_metric = False

    def plugin_init(self):
        self.metric = []
        for each_metric in self.metric_define:
            if each_metric.startswith('node') and each_metric != 'node.id' \
               and each_metric != 'node.type':
                self.metric.append(each_metric.split('.')[1])

        return super(StormTopologyCollector, self).plugin_init()

    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 8080)
        config.setdefault('uri', '/api/v1/topology/')
        config.setdefault('timeout', 5)
        self.url = 'http://%s:%s%s' % (config['host'], config['port'], config['uri'])
        return config


    def check(self, config):
        report_data = self.__report_all_topologies(config)

        return report_data

    def __get_topology_summary(self, config):
        url = self.url + 'summary'
        timeout = config.get("timeout", 5)
        summary_topologies = json.loads(do_http('GET', url, params={}, timeout=timeout))
        topologies = summary_topologies.get('topologies')

        return topologies

    def __get_topology_detail(self, topology_id, config):
        url = self.url + topology_id
        timeout = config.get("timeout", 5)
        topology = json.loads(do_http('GET', url, params={}, timeout=timeout))

        return topology

    def __report_topology(self, topology):
        report_nodes = []

        common = {
            'topology.uptime': topology.get('uptime'),
            'topology.status': topology.get('status'),
            'topology.id': topology.get('id')
        }
        spouts = topology.get('spouts')
        bolts = topology.get('bolts')

        for spout in spouts:
            node = self.__report_node(common, spout, 'spout')
            report_nodes.append(node)

        for bolt in bolts:
            node = self.__report_node(common, bolt, 'bolt')
            report_nodes.append(node)

        return report_nodes

    def __report_node(self, common, node, style='bolt'):
        if style == 'bolt':
            report_node = {
                'node.type': 'bolt',
                'node.id': node['boltId']
            }
        else:
            report_node = {
                'node.type': 'spout',
                'node.id': node['spoutId']
            }
        report_node.update(common)
        for metric in self.metric:
            key = 'node.' + metric
            report_node[key] = node.get(metric, 0)

        return report_node

    def __report_all_topologies(self, config):
        topologies_summary = self.__get_topology_summary(config)
        report_data = []

        for topology in topologies_summary:
            topology_id = topology.get('id')
            topology_detail = self.__get_topology_detail(topology_id, config)
            report_topology = self.__report_topology(topology_detail)

            report_data.extend(report_topology)

        return report_data
