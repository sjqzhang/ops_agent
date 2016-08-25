#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import traceback
from collections import deque
import json
import gevent

from easy_plugin import EasyPlugin
from libs.report import report, report_json


CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))


class EasyCollectorExcept(Exception):
    """"""


class EasyCollector(EasyPlugin):
    # 采集实例配置folder
    instance_config_folder = os.path.join(CURRENT_FOLDER, '../data')
    # 组件名称，用来做指标名的前缀
    component = ''
    #上报的data_id，3200将会写到collector这个topic，如果需要写到其他topic，可修改data_id
    data_id = 3200
    # 指标的定义
    # 格式为{metric_name: {"type": type}}
    # type可选为：gauge，counter，text
    # 如：
    # {"load.1": {"type": "gauge", "unit": "n", "name": u'1分钟负载', "info": ""}}
    # {"packages": {"type": "counter", "max": 65535}}
    metric_define = {

    }
    # 指标说明版本号, 版本号越大， 指标说明越新
    # 个位数是大版本的版本号， 各个组件请用小数维护自己的版本号
    metric_define_version = 1

    # 缓存的长度
    cache_maxlen = 3
    # 是否允许上传没在定义中的指标
    # 如磁盘等不能统一的命名则需打开这个开关，这种指标类型为gauge
    allow_undefined_metric = False
    # 初始化下拉配置
    sync_count = 3
    # 最大text长度限制
    max_text_length = 10000

    version = ''

    # 组件采集的超时时间, 默认 10s
    check_timeout = 10

    def __init__(self, *args, **kwargs):
        if not self.component:
            raise NotImplementedError()
        super(EasyCollector, self).__init__(*args, **kwargs)
        self._store = {}
        self.last_run_time = 0
        self.timecost = 0
        # 是否已上报字段信息。每个插件第一次采集到数据时都上报一次
        self.report_metric_info_flag = False
        # 实例配置文件
        self.instance_config_file = os.path.join(self.instance_config_folder, '%s.json' %self.name)
        self.config_mtime = 0
        self.instance = []

    def plugin_init(self):
        if not os.path.isdir(self.instance_config_folder):
            self.logger.error('not found %s folder, please create first' %(self.instance_config_folder))
            sys.exit(1)
        self.config = self.config or {}
        return super(EasyCollector, self).plugin_init()

    def format_metric_name(self, key):
        # name = re.sub(r"[,\+\*\-/()\[\]{}]", "_", key).lower()
        # name = '.'.join(name.split('_'))
        name = key
        if self.component:
            return self.component + "." + name
        else:
            return name

    def limit_text_len(self, s):
        if not self.max_text_length:
            return s

        if isinstance(s, (str, unicode)) and len(s) > self.max_text_length:
            return s[:self.max_text_length] + '...'
        else:
            return s

    def store_value(self, key, value, _type):
        """把结果压入缓存中"""
        if key not in self._store:
            maxlen = 1 if _type == 'text' else self.cache_maxlen
            self._store[key] = deque(maxlen=maxlen)
        if _type == 'text':
            self._store[key].append(self.limit_text_len(value))
        else:
            try:
                value = int(round(float(value),0))
            except (ValueError, TypeError),e:
                value = 0
            self._store[key].append(value)

    def shape_value(self, key, _type):
        """滤波整形"""
        if _type == 'text':
            return self._store[key][-1]
        elif _type == 'counter':
            return self.shape_counter_value(key)
        else:
            return self.shape_gauge_value(key)

    def shape_counter_value(self, key):
        """counter整形"""
        if len(self._store[key]) < 2:
            return None
        else:
            val = self._store[key][-1] - self._store[key][-2]
            if val >= 0:
                return val
            # 超出最大值，复位
            else:
                max_value = self.metric_define.get(key, {}).get('max')
                if not max_value:
                    return 0
                else:
                    return max_value-self._store[key][-2]+self._store[key][-1]

    def shape_gauge_value(self, key):
        """值整形，目前直接取最后一个"""
        return self._store[key][-1]

    def shape_all_values(self, data):
        """有一些key需要依赖于其他的key来shape"""
        # 注意这里data是引用类型，而且这时候key已经有经过format_name的了
        pass

    def _report(self, data_id, vals={}, dims={}):
        # pass
        # print dims,vals
        try:
            if data_id in (1100, 1205, 1301, 3210, 3220, 3505, 3515, 3605):# 指标说明，主机资产采集，配置同步，拓扑采集，自定义对象采集
                ret = report_json(data_id, vals=vals, dims=dims)# json上报
            else:
                ret = report(data_id, vals=vals, dims=dims)# pb上报
        except Exception,e:
            self.logger.error(traceback.format_exc())
            ret = (1, e.message or unicode(e))
        return ret

    def report_value(self, data, dims=None):
        """调用agent的sdk上传结果"""
        if dims is None:
            dims = {}

        if self.version:
            dims['version'] = self.version

        return self._report(self.data_id, vals=data, dims=dict(dims, name=self.component))

    def report_metric_info(self):
        fields = []
        keys = self._store.keys()
        keys += self.metric_define.keys()
        for key in set(keys):
            field = self.metric_define.get(key, {'type': 'gauge'})
            field['key'] = self.format_metric_name(key)
            fields.append(field)
        return self._report(
            3210,
            vals={'name': self.component, 'fields': fields, 'version': self.metric_define_version},
            dims={'name': self.component}
        )

    def get_instances(self):
        if not os.path.isfile(self.instance_config_file):
            return None
        # 通过修改时间判断配置文件是否有修改
        mtime = os.path.getmtime(self.instance_config_file)
        if self.config_mtime == mtime:
            return self.instances
        self.config_mtime = mtime
        with open(self.instance_config_file) as fp:
            try:
                instances = json.load(fp).get(self.name, [])
            except:#有可能配置文件非json格式，解析错误
                self.logger.error('%s is not json file' %self.instance_config_file)
                return None
        if not isinstance(instances, list):
            self.logger.error('%s config error, should be list. please check in %s' %(self.name, self.instance_config_file))
            return None
        return instances

    def fill_default_config(self, config):
        config['timeout'] = 5
        return config

    def handle_timer(self):
        # 没开启采集
        datas = []
        if self.config.get('disabled', False):
            return datas
        # 获得采集实例
        instances = self.get_instances()
        if instances is None:
            return datas
        self.instances = instances
        self.last_run_time = time.time()
        # 定期同步
        self.sync_config()
        # 开始采集
        try:
            for instance in self.instances:
                config = self.fill_default_config(instance)
                datas = self._check(config)
                if datas:
                    dims = {'port': config['port']} if 'port' in config else {}
                    self.report_value(datas, dims)
                    if not self.report_metric_info_flag:
                        self.report_metric_info()
                        self.report_metric_info_flag = True
                gevent.sleep()
        except Exception, e:
            self.logger.error(traceback.format_exc())
        self.timecost = round(time.time() - self.last_run_time, 4)
        self.logger.info('%s run, timecost is %s' %(self.__class__.__name__, self.timecost))
        return datas

    def _check(self, config):
        data = None
        with gevent.Timeout(self.check_timeout, False):
            data = self.format_return(self.check(config))

        if data is None:
            self.logger.error('collection is timeout, component: {0}, timeout: {1}'.format(self.component,
                                                                                           self.check_timeout))
        return data

    def check(self, config={}):
        """
        采集，返回有两种格式：
        只返回1个字典，这个字典将作为vals上报
        @return: {"load.1": 1, "load.5": 5}
        返回1个列表，
        @return: [{"node.emit": 11}]
        """
        return {"load.1": 1, "load.5": 5}


    def format_return(self, result):
        datas = []
        if not result:
            return datas
        if isinstance(result, dict):
            result_list = [result]
        else:
            result_list = result
        for result in result_list:
            data = {}
            # print result
            for key, value in result.iteritems():
                if key not in self.metric_define:
                    if self.allow_undefined_metric:
                        _type = 'gauge'
                    else:
                        # self.logger.warning('found not defind metric "%s" and disallow undefine metric, will discard it' %key)
                        continue
                else:
                    _type = self.metric_define[key]['type']
                self.store_value(key, value, _type)
                data[self.format_metric_name(key)] = self.shape_value(key, _type)
            self.shape_all_values(data)
            datas.append(data)
        return datas


    # data process
    def _convert_to_float(self, value):
        try:
            val = float(value) if value else 0.0
        except:
            val = 0.0

        return val

    def _millisecond_convert_to_second(self, microsecond):
        microsecond = self._convert_to_float(microsecond)
        return microsecond / 1000

    def _byte_convert_to_kbyte(self, byte):
        byte = self._convert_to_float(byte)
        return byte / 1024

    def _mbyte_convert_to_kbyte(self, mbyte):
        mbyte = self._convert_to_float(mbyte)
        return mbyte * 1024

    def _decimal_convert_to_percent(self, decimal):
        decimal = self._convert_to_float(decimal)
        return decimal * 100

    def sync_config(self):
        EasyCollector.sync_count -= 1
        # 1分钟1次的话，300分钟（5小时）同步一次配置
        if EasyCollector.sync_count <= 0:
            gevent.sleep(3)
            EasyCollector.sync_count = 300
            self.logger.info('sync config now ...')
            self._report(3220, vals={'init': 1})
