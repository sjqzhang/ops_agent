#!/usr/local/easyops/python/bin/python
#-*- coding: utf-8 -*-

from collector.easy_collector import EasyCollector
import collector.easy_collector
import time


class LogCollector(EasyCollector):
    METRIC_DIM = 0
    METRIC_VAL = 1

    data_id = 3300
    component = 'route'
    # 日志格式： 时间戳`parent_id`request_id`step_id`主调名字`主调IP`被调名字`被调接口`被调IP`被调端口`调用状态`调用延时`代码位置`错误堆栈`预留字段
    metric_define = {
        'route.route.ts': {"type": "gauge", "unit": "", "name": u'时间戳', "info": ""},
        'route.route.parent_id': {"type": "gauge", "unit": "", "name": u'父请求ID', "info": "", "field_type": "dim"},
        'route.route.request_id': {"type": "gauge", "unit": "", "name": u'请求ID', "info": "", "field_type": "dim"},
        'route.route.step_id': {"type": "gauge", "unit": "", "name": u'步骤ID', "info": "", "field_type": "dim"},
        'route.route.src_name': {"type": "gauge", "unit": "", "name": u'主调名字', "info": "", "field_type": "dim"},
        'route.route.src_ip': {"type": "gauge", "unit": "", "name": u'主调IP', "info": "", "field_type": "dim"},
        'route.route.dst_name': {"type": "gauge", "unit": "", "name": u'被调名字', "info": "", "field_type": "dim"},
        'route.route.dst_raw_interface': {"type": "gauge", "unit": "", "name": u'被调接口', "info": "", "field_type": "dim"},
        'route.route.dst_ip': {"type": "gauge", "unit": "", "name": u'被调IP', "info": "", "field_type": "dim"},
        'route.route.dst_port': {"type": "gauge", "unit": "", "name": u'被调接口', "info": "", "field_type": "dim"},
        'route.route.ret_code': {"type": "gauge", "unit": "", "name": u'调用返回码', "info": ""},
        'route.route.delay': {"type": "gauge", "unit": "", "name": u'调用延时', "info": ""},
        'route.route.cp': {"type": "gauge", "unit": "", "name": u'代码位置', "info": ""},
        'route.route.stack': {"type": "gauge", "unit": "", "name": u'调用堆栈', "info": ""},
        'route.route.reserved': {"type": "gauge", "unit": "", "name": u'预留字段', "info": ""},
    }
    metrics = [('route.route.ts', METRIC_VAL, int), ('route.route.parent_id', METRIC_VAL, str),
               ('route.route.request_id', METRIC_VAL, str), ('route.route.step_id', METRIC_VAL, str),
               ('route.route.src_name', METRIC_VAL, str), ('route.route.src_ip', METRIC_VAL, str),
               ('route.route.dst_name', METRIC_VAL, str), ('route.route.dst_raw_interface', METRIC_VAL, str),
               ('route.route.dst_ip', METRIC_VAL, str), ('route.route.dst_port', METRIC_VAL, int),
               ('route.route.ret_code', METRIC_VAL, int), ('route.route.delay', METRIC_VAL, int),
               ('route.route.cp', METRIC_VAL, str), ('route.route.stack', METRIC_VAL, str),
               ('route.route.reserved', METRIC_VAL, str)]

    def plugin_init(self):
        # file_name: (file, st_ino, st_dev, position)
        self.files = {}
        self._report_start_time = 0
        self._report_count_in_one_second = 0
        return EasyCollector.plugin_init(self)

    def _check(self, conf):
        remove_files = []
        for file_name, file_tuple in self.files.iteritems():
            file, _, _ = file_tuple
            while True:
                try:
                    line = file.readline()
                except Exception, e:
                    file.close()
                    remove_files.append(file_name)
                    break

                if line:
                    data = self._handle_log(line.strip())
                    if data is None:
                        continue

                    if self._overload():
                        break

                    self.report_value(data)
                else:
                    break

        for file_name in remove_files:
            pop_file = self.files.pop(file_name, None)
            if pop_file is not None:
                pop_file.close()

        return None

    # @collector.easy_collector.format_return
    def _handle_log(self, line):
        try:
            components = self._process_line(line)
        except Exception, e:
            self.logger.error("process line error, {}, {}".format(line, e))
            return None

        if components is None:
            return None
        try:
            vals = self._format_components(components)
        except Exception, e:
            self.logger.error("format components error, {}, {}".format(components, e))
            return None
        return vals

    def _process_line(self, line):
        components = line.split("`")
        if len(components) != len(LogCollector.metric_define):
            return None
        return components

    def _format_components(self, components):
        idx = 0
        dims = {}
        vals = {}
        for metric_info in self.metrics:
            metric_name, metric_kind, metric_type = metric_info
            if components[idx] == '' and metric_type is int:
                components[idx] = -1
            if metric_kind == LogCollector.METRIC_DIM:
                dims[metric_name] = metric_type(components[idx])
            elif metric_kind == LogCollector.METRIC_VAL:
                vals[metric_name] = metric_type(components[idx])
            idx += 1

        return vals

    def get_instances(self):
        return [{}]

    def _overload(self):
        if time.time() - self._report_start_time >= 1:
            if self._report_count_in_one_second > self.config["max_log_report_per_sec"]:
                self.logger.warning("log overload!!! log_in_one_second={}".format(self._report_count_in_one_second))

            self._report_start_time = time.time()
            self._report_count_in_one_second = 0
        self._report_count_in_one_second += 1
        if self._report_count_in_one_second > self.config["max_log_report_per_sec"]:
            return True
        return False

