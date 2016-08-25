#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

'''
Parses the response from zookeeper's `stat` admin command, which looks like:

```
Zookeeper version: 3.4.6-1569965, built on 02/20/2014 09:09 GMT
Clients:
 /192.168.100.109:55036[1](queued=0,recved=53,sent=53)
 /192.168.100.109:55038[1](queued=0,recved=1,sent=1)
 /192.168.100.109:50284[1](queued=0,recved=23241,sent=23241)
 /192.168.100.109:50288[1](queued=0,recved=4862,sent=4998)
 /192.168.100.109:55037[1](queued=0,recved=18,sent=18)
 /192.168.100.109:55032[1](queued=0,recved=54,sent=54)
 /192.168.100.109:55039[1](queued=0,recved=4,sent=4)
 /127.0.0.1:55495[0](queued=0,recved=1,sent=0)

Latency min/avg/max: 0/19/3276
Received: 64231
Sent: 64356
Connections: 8
Outstanding: 0
Zxid: 0x22000c439a
Mode: follower
Node count: 440
```

Tested with Zookeeper versions 3.0.0 to 3.4.6

'''

from gevent import socket
import StringIO
import struct
import re

from collector.jvm_collector import JvmCollector


class ZookeeperCollector(JvmCollector):
    component = "zookeeper"

    metric_define = {
        "latency.min": {"type": "gauge", "unit": "", "name": u"请求时延最小值", "info": ""},
        "latency.avg": {"type": "gauge", "unit": "", "name": u"请求时延平均值", "info": ""},
        "latency.max": {"type": "gauge", "unit": "", "name": u"请求时延最大值", "info": ""},

        "bytes.received": {"type": "counter", "unit": "KB", "name": u"网络接收流量", "info": ""},
        "bytes.sent": {"type": "counter", "unit": "KB", "name": u"网络发送流量", "info": ""},

        "current.connections": {"type": "gauge", "unit": "", "name": u"当前的连接数", "info": ""},
        "outstanding.connections": {"type": "gauge", "unit": "", "name": u"未处理的连接数", "info": ""},

        # todo 未理解指标
        "zxid.epoch": {"type": "gauge", "unit": "", "name": u"zxid.epoch", "info": ""},
        "zxid.count": {"type": "gauge", "unit": "", "name": u"zxid.count", "info": ""},

        "server.mode": {"type": "gauge", "unit": "", "name": u"集群模式", "info": ""},
        "server.status":
            {"type": "gauge", "unit": "", "name": u"当前状态", "info": u"当前zookeeper server的状态, 0为OK, 如果为1, 服务可能存在问题"},

        "node.count": {"type": "gauge", "unit": "", "name": u"节点数量", "info": ""}
    }

    metric_define.update(JvmCollector.metric_define)
    allow_undefined_metric = False

    data = {}
    version_pattern = re.compile(r'Zookeeper version: ([^.]+)\.([^.]+)\.([^-]+)', flags=re.I)

    def fill_default_config(self, config):
        super(ZookeeperCollector, self).fill_default_config(config)
        config.setdefault('zkcli_port', 2181)
        return config

    def check(self, config):
        self.data = super(ZookeeperCollector, self).check(config)

        try:
            # command args
            cx_args = (config['host'], config['zkcli_port'], config['timeout'])

            # Read metrics from the `stat` output.
            stat_out = self._send_command('stat', *cx_args)
            self.data = self.parse_stat(stat_out, self.data)

            # Read status from the `ruok` output.
            ruok_out = self._send_command('ruok', *cx_args)
            ruok_out.seek(0)
            ruok = ruok_out.readline().strip()

            if ruok == 'imok':
                self.data['server.status'] = 0
            else:
                self.data['server.status'] = 1
        except Exception, e:
            print e.message
        finally:
            return self.data

    def _send_command(self, command, host, port, timeout):
        sock = socket.socket()
        sock.settimeout(timeout)
        buf = StringIO.StringIO()
        chunk_size = 4096
        # try-finally and try-except to stay compatible with python 2.4
        try:
            try:
                # Connect to the zk client port and send the stat command
                sock.connect((host, port))
                sock.sendall(command)

                # Read the response into a StringIO buffer
                chunk = sock.recv(chunk_size)
                buf.write(chunk)
                num_reads = 1
                max_reads = 100
                while chunk:
                    if num_reads > max_reads:
                        # Safeguard against an infinite loop
                        raise Exception("Read %s bytes before exceeding max reads of %s. "
                                        % (buf.tell(), max_reads))
                    chunk = sock.recv(chunk_size)
                    buf.write(chunk)
                    num_reads += 1
            except (socket.timeout, socket.error):
                raise Exception("the execution of command is timeout")
        finally:
            sock.close()
        return buf

    def parse_stat(self, buf, data):
        buf.seek(0)

        # 检测 zk 版本, stat 命令信息中 Connections 在 3.4.4 或者以上的版本才支持
        # Zookeeper version: 3.4.6-1569965, built on 02/20/2014 09:09 GMT
        start_line = buf.readline()
        match = self.version_pattern.match(start_line)
        if match is None:
            raise Exception("Could not parse version from stat command output: %s" % start_line)
        else:
            version_tuple = match.groups()
        has_connections_val = version_tuple >= ('3', '4', '4')

        # 接下来是 Clients 区域, 先跳一行, 然后接下来直到空行为止, 一个 connection 就是一行
        '''
        Clients:
         /192.168.100.109:55036[1](queued=0,recved=53,sent=53)
         /192.168.100.109:55038[1](queued=0,recved=1,sent=1)
         /192.168.100.109:50284[1](queued=0,recved=23241,sent=23241)
         /192.168.100.109:50288[1](queued=0,recved=4862,sent=4998)
         /192.168.100.109:55037[1](queued=0,recved=18,sent=18)
         /192.168.100.109:55032[1](queued=0,recved=54,sent=54)
         /192.168.100.109:55039[1](queued=0,recved=4,sent=4)
         /127.0.0.1:55495[0](queued=0,recved=1,sent=0)

        '''
        buf.readline()
        connections = 0
        client_line = buf.readline().strip()
        if client_line:
            connections += 1
        while client_line:
            client_line = buf.readline().strip()
            if client_line:
                connections += 1

        # Latency min/avg/max: 0/19/3276
        _, value = buf.readline().split(':')
        l_min, l_avg, l_max = [int(v) for v in value.strip().split('/')]
        data['latency.min'] = self._convert_to_float(l_min)
        data['latency.avg'] = self._convert_to_float(l_avg)
        data['latency.max'] = self._convert_to_float(l_max)

        # Received: 64231
        _, value = buf.readline().split(':')
        data['bytes.received'] = self._convert_to_float(value.strip())

        # Sent: 64356
        _, value = buf.readline().split(':')
        data['bytes.sent'] = self._convert_to_float(value.strip())

        # Connections: 8
        if has_connections_val:
            _, value = buf.readline().split(':')
            data['current.connections'] = self._convert_to_float(value.strip())
        else:
            data['current.connections'] = connections

        # Outstanding: 0
        _, value = buf.readline().split(':')
        data['outstanding.connections'] = self._convert_to_float(value.strip())

        # Zxid: 0x22000c439a
        _, value = buf.readline().split(':')
        # Parse as a 64 bit hex int
        zxid = long(value.strip(), 16)
        # convert to bytes
        zxid_bytes = struct.pack('>q', zxid)
        # the higher order 4 bytes is the epoch
        (zxid_epoch,) = struct.unpack('>i', zxid_bytes[0:4])
        # the lower order 4 bytes is the count
        (zxid_count,) = struct.unpack('>i', zxid_bytes[4:8])

        data['zxid.epoch'] = self._convert_to_float(zxid_epoch)
        data['zxid.count'] = self._convert_to_float(zxid_count)

        # Mode: follower
        _, value = buf.readline().split(':')
        data["server.mode"] = value.strip().lower()

        # Node count: 440
        _, value = buf.readline().split(':')
        data['node.count'] = self._convert_to_float(value.strip())

        return data



