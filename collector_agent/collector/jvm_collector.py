#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
import os
import json
import traceback
import subprocess
import gevent
from gevent import socket


from collector.easy_collector import EasyCollector, EasyCollectorExcept


ROOT_FOLDER = os.path.join(os.path.dirname(__file__), '..')

JSTATUS = {
    'ip': 'localhost',
    'port': 8090,
    'path': os.path.join(ROOT_FOLDER, 'libs', 'jstatus-1.0-SNAPSHOT-jar-with-dependencies.jar'), 
    'conf': os.path.join(ROOT_FOLDER, 'libs', 'jstatus'), 
    'data': os.path.join(ROOT_FOLDER, 'data'), 
    'log': os.path.join(ROOT_FOLDER, 'log', 'jstatus.log'),
    'log_level': 'DEBUG',
    'new_jvm_option': '-server -Xms64M -Xmx64M -XX:MaxMetaspaceSize=16m -Djava.net.preferIPv4Stack=true',
    'old_jvm_option': '-server -Xms64M -Xmx64M -XX:MaxPermSize=16m -Djava.net.preferIPv4Stack=true'
}


class JvmCollectorExcept(EasyCollectorExcept):
    code = 2001


class JvmCollector(EasyCollector):
    component = 'jvm'
    metric_define = {
        # heap memory usage
        "heap.max": {"type": "gauge", "unit": "KB", "name": u"堆内存总大小", "info": ""},
        "heap.committed": {"type": "gauge", "unit": "KB", "name": u"堆内存已分配内存", "info": ""},
        "heap.used": {"type": "gauge", "unit": "KB", "name": u"堆内存已使用内存", "info": ""},

        # thread information
        "thread.count": {"type": "gauge", "unit": "", "name": u"线程数量", "info": ""},
        "daemon_thread.count": {"type": "gauge", "unit": "", "name": u"后台线程数量", "info": ""},

        # YGC
        "ygc.count": {"type": "counter", "unit": "", "name": u"YGC次数", "info": ""},
        "ygc.time": {"type": "counter", "unit": "ms", "name": u"YGC所用时间", "info": ""},

        # FGC
        "fgc.count": {"type": "counter", "unit": "", "name": u"FGC次数", "info": ""},
        "fgc.time": {"type": "counter", "unit": "ms", "name": u"FGC所用时间", "info": ""},

        # dynamic memory pool
        # Meta Space
        "metaspace.max": {"type": "gauge", "unit": "KB",
                          "name": u"MetaSpace总大小", "info": u""},
        "metaspace.used": {"type": "gauge", "unit": "KB",
                           "name": u"MetaSpace已使用内存", "info": u""},
        "metaspace.committed": {"type": "gauge", "unit": "KB",
                                "name": u"MetaSpace已分配内存", "info": u""},

        # The Concurrent Mark Sweep (CMS) Collector
        # CMS PerGem Space
        "cms_perm_gen.max": {"type": "gauge", "unit": "KB", "name": u"PerGem Space总大小(CMS算法)", "info": ""},
        "cms_perm_gen.used": {"type": "gauge", "unit": "KB", "name": u"PerGem Space已使用内存(CMS算法)", "info": ""},
        "cms_perm_gen.committed": {"type": "gauge", "unit": "KB", "name": u"PerGem Space已分配内存(CMS算法)", "info": ""},

        # CMS Old Space
        "cms_old_gen.max": {"type": "gauge", "unit": "KB", "name": u"OldSpace总大小(CMS算法)", "info": ""},
        "cms_old_gen.used": {"type": "gauge", "unit": "KB", "name": u"OldSpace已使用内存(CMS算法)", "info": ""},
        "cms_old_gen.committed": {"type": "gauge", "unit": "KB", "name": u"OldSpace已分配内存(CMS算法)", "info": ""},

        # CMS Eden Space
        "par_eden_space.max": {"type": "gauge", "unit": "KB", "name": u"EdenSpace总大小(CMS算法)", "info": ""},
        "par_eden_space.used": {"type": "gauge", "unit": "KB", "name": u"EdenSpace已使用内存(CMS算法)", "info": ""},
        "par_eden_space.committed": {"type": "gauge", "unit": "KB",
                                     "name": u"EdenSpace已分配内存(CMS算法)", "info": ""},

        # CMS Survivor Space
        "par_survivor_space.max": {"type": "gauge", "unit": "KB", "name": u"SurvivorSpace总大小(CMS算法)", "info": ""},
        "par_survivor_space.used": {"type": "gauge", "unit": "KB",
                                    "name": u"SurvivorSpace已使用内存(CMS算法)", "info": ""},
        "par_survivor_space.committed": {"type": "gauge", "unit": "KB",
                                         "name": u"SurvivorSpace已分配内存(CMS算法)", "info": ""},

        # The Parallel GC Collector
        # PS PerGem Space
        "ps_perm_gen.max": {"type": "gauge", "unit": "KB", "name": u"PerGem Space总大小(并行回收算法)", "info": ""},
        "ps_perm_gen.used": {"type": "gauge", "unit": "KB", "name": u"PerGem Space已使用内存(并行回收算法)", "info": ""},
        "ps_perm_gen.committed": {"type": "gauge", "unit": "KB", "name": u"PerGem Space已分配内存(并行回收算法)", "info": ""},

        # PS Old Space
        "ps_old_gen.max": {"type": "gauge", "unit": "KB", "name": u"OldSpace总大小(并行回收算法)", "info": ""},
        "ps_old_gen.used": {"type": "gauge", "unit": "KB", "name": u"OldSpace已使用内存(并行回收算法)", "info": ""},
        "ps_old_gen.committed": {"type": "gauge", "unit": "KB", "name": u"OldSpace已分配内存(并行回收算法)", "info": ""},

        # PS Eden Space
        "ps_eden_space.max": {"type": "gauge", "unit": "KB", "name": u"EdenSpace总大小(并行回收算法)", "info": ""},
        "ps_eden_space.used": {"type": "gauge", "unit": "KB", "name": u"EdenSpace已使用内存(并行回收算法)", "info": ""},
        "ps_eden_space.committed": {"type": "gauge", "unit": "KB", "name": u"EdenSpace已分配内存(并行回收算法)", "info": ""},

        # PS Survivor Space
        "ps_survivor_space.max": {"type": "gauge", "unit": "KB", "name": u"SurvivorSpace总大小(并行回收算法)", "info": ""},
        "ps_survivor_space.used": {"type": "gauge", "unit": "KB",
                                   "name": u"SurvivorSpace已使用内存(并行回收算法)", "info": ""},
        "ps_survivor_space.committed": {"type": "gauge", "unit": "KB",
                                        "name": u"SurvivorSpace已分配内存(并行回收算法)", "info": ""}
    }

    metric_transform_to_kbyte = [
        "heap.max",
        "heap.committed",
        "heap.used",

        "metaspace.max",
        "metaspace.used",
        "metaspace.committed",

        "cms_perm_gen.max",
        "cms_perm_gen.used"
        "cms_perm_gen.committed",

        "cms_old_gen.max",
        "cms_old_gen.used",
        "cms_old_gen.committed",

        "par_eden_space.max",
        "par_eden_space.used",
        "par_eden_space.committed",

        "par_survivor_space.max",
        "par_survivor_space.used",
        "par_survivor_space.committed",

        "ps_perm_gen.max",
        "ps_perm_gen.used",
        "ps_perm_gen.committed",

        "ps_old_gen.max",
        "ps_old_gen.used",
        "ps_old_gen.committed",

        "ps_eden_space.max",
        "ps_eden_space.used",
        "ps_eden_space.committed",

        "ps_survivor_space.max",
        "ps_survivor_space.used",
        "ps_survivor_space.committed"
    ]

    allow_undefined_metric = False
    jstatus_ip = JSTATUS['ip']
    jstatus_port = JSTATUS['port']
    jstatus_path = JSTATUS['path']
    jstatus_conf = JSTATUS['conf']
    jstatus_data = JSTATUS['data']
    jstatus_log = JSTATUS['log']
    jstatus_log_level = JSTATUS['log_level']

    def fill_default_config(self, config):
        config.setdefault('host', '127.0.0.1')
        config.setdefault('port', 10000)
        config.setdefault('timeout', 12)
        config.setdefault('java_bin', 'java')
        return config

    # def plugin_init(self):
    #     try:
    #         self.socket = self.get_socket()
    #     except Exception,e:
    #         self.logger.error(traceback.print_exc())
    #         return 1, 'connect to jstatus error: %s' %e.message
    #     self.inst_id = self._init_jmx_conf()
    #     return super(JvmCollector, self).plugin_init()


    def get_socket(self, config):
        def _get_socket():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.jstatus_ip, self.jstatus_port))
            s.settimeout(config['timeout'])
            return s
        try:
            self.socket_line_prefix = ''
            self.already_reload = False
            return _get_socket()
        except:
            self.start_jstatus_process(config['java_bin'])
            return _get_socket()

    def get_jvm_option(self, java_bin):
        cmd = '%s -version 2>&1 | grep \' version \' | awk -F"[\\"_]" \'{print $2}\'' %java_bin
        popen = subprocess.Popen(cmd, shell=True, close_fds=True, stdout=subprocess.PIPE)
        excute_data = popen.stdout.readlines()
        try:
                version = excute_data[0].strip('\n')
                major, minor, security = [int(x) for x in version.split('.')]
                if major > 1 or minor >= 8:
                    self.logger.info("using jdk version: {0}, "
                                     "set JVM option with MetaSpace parameter".format(excute_data))
                    return JSTATUS['new_jvm_option']

                else:
                    self.logger.info("using jdk version: {0}, "
                                     "set JVM option with PermSpace parameter".format(excute_data))
                    return JSTATUS['old_jvm_option']

        except Exception as msg:
                self.logger.error("failed to decide the java version from excute_data: {0}, "
                                  "exception msg: {1}".format(excute_data, msg))

                self.logger.error(traceback.format_exc())
                raise JvmCollectorExcept('receive java version error')

    def start_jstatus_process(self, java_bin):
        self.jstatus_jvm_option = self.get_jvm_option(java_bin)
        cmd = '%s %s -jar %s -D %s -L %s -l %s -P %s start' % (
            java_bin,
            self.jstatus_jvm_option, 
            self.jstatus_path, 
            self.jstatus_data, 
            self.jstatus_log_level, 
            self.jstatus_log,
            self.jstatus_port
        )
        cmd = 'nohup %s &' % cmd
        popen = subprocess.Popen(cmd, shell=True, close_fds=True)
        popen.communicate()
        code = popen.returncode
        if not code:
            self.logger.info('start jstatus success')
        else:
            raise JvmCollectorExcept('start jstatus error')
        gevent.sleep(10)

    def _init_jmx_conf(self, config):
        try:
            inst_id = '%s_%s_%s' %(self.component, config['host'], config['port'])
            conf_file = os.path.join(self.jstatus_data, '%s.yaml' %(inst_id))
            # if os.path.isfile(conf_file):# Todo 如果用户名密码有修改的话就会得不到变更
            #     return inst_id
            sample_conf_file = os.path.join(self.jstatus_conf, '%s.yaml.sample' %self.component)
            if not os.path.isfile(sample_conf_file):
                raise JvmCollectorExcept('not found sample config file: %s' %sample_conf_file)
            with open(sample_conf_file, 'r') as fp:
                sample_conf = fp.read()
            conf = sample_conf.replace(
                '[host]', config['host']
            ).replace(
                '[port]', str(config['port'])
            ).replace(
                '[username]', config.get('username', ''),
            ).replace(
                '[password]', config.get('password', ''),
            )
            with open(conf_file, 'w') as fp:
                fp.write(conf)
            # self.reload_instance(self.inst_id)
        except Exception, e:
            self.logger.error(traceback.format_exc())
        return inst_id

    def _read_line(self, s):
        """一行一行读"""
        count = 0
        val = '{}'
        while count<10:
            rval = s.recv(4096)
            if '\n' in rval:
                tmp = rval.split('\n', 1)
                val = self.socket_line_prefix + tmp[0]
                self.socket_line_prefix = tmp[1]
                break
            else:
                self.socket_line_prefix += rval
            count += 1
            gevent.sleep(0)
        return val

    def _send_line(self, s, data):
        """一行一行发"""
        try:
            s.sendall(data+'\n')
        except socket.error, e:
            # 表示 jstatus 没启动
            if e[0] == 32:
                self.socket = self.get_socket()
            else:
                raise

    def _send_data(self, data):
        self._send_line(self.socket, json.dumps(data))
        return self._read_line(self.socket).strip()

    def reload_instance(self, inst_id):
        return self._send_data({
            'instruction': 'RELOAD',
            'data': inst_id
        })

    def get_collector(self, inst_id):
        return self._send_data({
            'instruction': 'COLLECT',
            'data': inst_id
        }) 

    def _parse_data(self, rvalue):
        try:
            rvalue = json.loads(rvalue)
        except ValueError, e:
            raise JvmCollectorExcept('return value should be json, bug found %s' % rvalue)

        # 该实例未启动，尝试启动
        if rvalue.get('code'):
            if "Can't match any instances with instance id" in rvalue.get('msg') and not self.already_reload:
                self.already_reload = True
                # 重载且只重载一次
                self.reload_instance(self.inst_id)
                return 1, {}
            else:
                raise JvmCollectorExcept('jstatus return error, %s' % rvalue.get('msg'))
        return 0, self._parse_dimension_value(rvalue.get('data', {}))

    def _parse_gc_time(self, obj, data):
        # The Parallel GC Collector :
        # YGC: ps scavenge; FGC: ps marksweep

        # The Concurrent Mark Sweep (CMS) Collector
        # YGC: parnew; FGC: concurrentmarksweep

        if obj.get('jmx_domain:java.lang,name:ps marksweep,type:garbagecollector') >= 0:
            data['fgc.time'] = obj.get('jmx_domain:java.lang,name:ps marksweep,type:garbagecollector')
        else:
            data['fgc.time'] = obj.get('jmx_domain:java.lang,name:concurrentmarksweep,type:garbagecollector')

        if obj.get('jmx_domain:java.lang,name:ps scavenge,type:garbagecollector') >= 0:
            data['ygc.time'] = obj.get('jmx_domain:java.lang,name:ps scavenge,type:garbagecollector')
        else:
            data['ygc.time'] = obj.get('jmx_domain:java.lang,name:parnew,type:garbagecollector')

    def _parse_gc_count(self, obj, data):
        # The Parallel GC Collector :
        # YGC: ps scavenge; FGC: ps marksweep

        # The Concurrent Mark Sweep (CMS) Collector
        # YGC: parnew; FGC: concurrentmarksweep

        if obj.get('jmx_domain:java.lang,name:ps marksweep,type:garbagecollector') >= 0:
            data['fgc.count'] = obj.get('jmx_domain:java.lang,name:ps marksweep,type:garbagecollector')
        else:
            data['fgc.count'] = obj.get('jmx_domain:java.lang,name:concurrentmarksweep,type:garbagecollector')

        if obj.get('jmx_domain:java.lang,name:ps scavenge,type:garbagecollector') >= 0:
            data['ygc.count'] = obj.get('jmx_domain:java.lang,name:ps scavenge,type:garbagecollector')
        else:
            data['ygc.count'] = obj.get('jmx_domain:java.lang,name:parnew,type:garbagecollector')

    def _parse_dimension_value(self, rvalue):
        """上报的数据可能是多维的"""
        data = {}
        dims = set()
        #Todo rvalue可能为unicode
        for key, obj in rvalue.iteritems():
            # 之后这里可能需要拆解为多个维度
            if key == 'gc.time':
                self._parse_gc_time(obj, data)

            elif key == 'gc.count':
                self._parse_gc_count(obj, data)

            else:
                total_val = sum(obj.values())
                data[key] = total_val
                # 以下代码都是为了检查数据，先观察哪些数据是多个维度的，之后再处理多维
                # 这个是有多少维度的
                dim_num = len(obj.keys())
                dims.add(dim_num)
                if dim_num != 1:
                    msg = 'there are %s dimension about %s in %s: %s' % (
                        dim_num,
                        key,
                        self.component,
                        ','.join(obj.keys())
                    )
                    self.logger.warning(msg)

        # 一次数据中最多只能有两种维度的数据，不能说A指标是一维的，B指标是二维的，C指标是三维的，这样没法处理
        if len(dims) > 2:
            self.logger.warning('there are %s dimension(%s) in %s, impossable!' % (
                len(dims), str(dims), self.component)
            )
        return data

    def close_socket(self):
        try:
            self.socket.close()
        except:
            pass

    def check(self, config):
        self.socket = self.get_socket(config)
        self.inst_id = self._init_jmx_conf(config)
        retry, data = self._parse_data(self.get_collector(self.inst_id))
        if retry:
            retry, data = self._parse_data(self.get_collector(self.inst_id))

        # data process
        for key, value in data.iteritems():
            if key in self.metric_transform_to_kbyte:
                data[key] = self._byte_convert_to_kbyte(data.get(key, 0))
        self.close_socket()
        return data


