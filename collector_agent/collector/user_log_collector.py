#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
import os
import logging
import time
import gevent
import re
import json
import traceback
from datetime import datetime
import sys
import ConfigParser
from libs.report import report_json
import xml.etree.ElementTree as ET
from libs import glob2
from collector.easy_collector import EasyCollector

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))


class ConifgManager:
    def __init__(self, config_file):
        self.config = config_file
        self.config_dict = {}
        self.files = {}
        self.last_changed_time = 0

        self.force_reload_interval = 15

    def parse_config(self):
        try:
            tree = ET.parse(self.config)
            root = tree.getroot()
            if "force_reload_interval" in root.attrib:
                self.force_reload_interval = int(root.attrib["force_reload_interval"])
            else:
                self.force_reload_interval = 15
            for log_node in root.findall("log_node"):
                self.config_dict[log_node.attrib["name"]] = {
                    "path": [],
                    "start_pos": log_node.attrib.get("start_pos", "end")
                }
                for path_node in log_node.findall("path"):
                    self.config_dict[log_node.attrib["name"]]["path"].append(path_node.text)
                exception_node = log_node.find("exception")
                exception_dict = {
                        "regular": None,
                        "max_lines": 100
                    }
                if exception_node is not None:
                    regular_node = exception_node.find("regular")
                    if regular_node is not None:
                        exception_dict["regular"] = regular_node.text
                    max_lines_node = exception_node.find("max_lines")
                    if max_lines_node is not None:
                        exception_dict["max_lines"] = int(max_lines_node.text)
                self.config_dict[log_node.attrib["name"]]["exception"] = exception_dict
            #print self.config_dict
            return True
        except Exception, e:
            print traceback.format_exc()
            exit(1)
            return False

    def get_files_by_config(self):
        if not os.path.isfile(self.config):
            return self.files
        file_stat = os.stat(self.config)
        if self.last_changed_time < file_stat.st_ctime and self.parse_config():
            self.files = self.find_files_by_patters()
            self.last_changed_time = file_stat.st_ctime
            return self.files
        elif time.time() - self.last_changed_time > self.force_reload_interval and self.parse_config():
            self.files = self.find_files_by_patters()
            self.last_changed_time = time.time()
            return self.files
        else:
            return self.files

    def find_files_by_patters(self):
        files_dict = {}
        for app_name, pattern_dict in self.config_dict.items():
            files_dict[app_name] = []
            for path in pattern_dict["path"]:
                files = glob2.glob(path)
                for file in files:
                    if file not in files_dict[app_name]:
                        files_dict[app_name].append(file)
        ret_files_dict = {}
        existed_files = []
        for app_name, files in files_dict.items():
            ret_files_dict[app_name] = []
            for file in files:
                if not os.path.isfile(file):
                    continue
                file_info = os.stat(file)
                if file not in existed_files:
                    existed_files.append((file, file_info.st_ino, file_info.st_dev))
                    ret_files_dict[app_name].append(
                        {
                            "base_info": (file, file_info.st_ino, file_info.st_dev),
                        }
                    )
        return ret_files_dict


class LogFile:
    def __init__(self, full_path, st_ino, st_dev, seek, logger):
        self.full_path = full_path
        self.st_ino = st_ino
        self.st_dev = st_dev

        self.data_id = 0
        self.app_name = ""

        self.fd = None
        self.read_seek_record = seek
        self.line_number = 0
        self.start_pos = "end"

        self.excepiton_regular = None
        self.compiled_pattern = None
        self.excepiton_max_lines = 100

        self.logger = logger

        self.max_read_lines_per_time = 10

        self.open_flag = False

        self.first_open = False
        self.last_date = None

        self.no_new_data_flag = False
        self.stopped_time = 0xffffffff

        self.no_such_file_flag = False

        self.last_line_str = ""

    def open_file(self):
        try:
            if UserLogCollector.opened_fd_num >= UserLogCollector.open_fd_max:
                return False
            self.fd = open(self.full_path)
            UserLogCollector.opened_fd_num += 1
            if self.read_seek_record != 0:
                self.fd.seek(self.read_seek_record, 0)
            self.open_flag = True
            if not self.first_open:
                self.last_date = datetime.now().date()
                self.first_open = True
            return True
        except Exception, e:
            self.logger.error(e.__unicode__() + self.full_path)
            return False

    def close_file(self):
        try:
            self.fd.close()
            UserLogCollector.opened_fd_num -= 1
        except Exception, e:
            self.logger.info(e.__unicode__())
        self.open_flag = False
        return

    def reset_seek_pos_by(self):
        date_now = datetime.now().date()
        if (date_now - self.last_date).days >= 1:
            self.read_seek_record = 0
            self.last_date = date_now

    def set_max_read_lines_per_time(self, num):
        self.max_read_lines_per_time = int(num)+1

    def set_no_data_flag(self):
        self.no_new_data_flag = True
        self.stopped_time = time.time()

    def format_data_dict(self, line_str):
        return_dict = {
            "path": self.full_path,
            "message": line_str,
            "lineno": self.line_number,
            "app_name": self.app_name,
            "report_time": int(time.time()*1000000)
        }
        return return_dict

    def report_last_line(self, report_func):
        if self.last_line_str != "":
            ret_dict = self.format_data_dict(self.last_line_str)
            ret_code = report_func(self.data_id, ret_dict)
            if not ret_code:
                self.logger.error("report error file:{file} line:{line}".format(file=self.full_path,
                                                                                line=self.last_line_str))
        self.read_seek_record = self.fd.tell()
        self.line_number += 1

    def read_line_handle(self, line_str, report_func):
        """
        report last one log
        :param line_str:
        :param report_func:
        :return:
        """
        def report(new_line_str, trace_err_flag=False):
            if self.last_line_str != "":
                log_str = self.last_line_str
                if trace_err_flag:
                    log_str += new_line_str
                    self.last_line_str = ""
                else:
                    self.last_line_str = new_line_str
                self.logger.debug("[debug] data_id: {a}".format(a=self.data_id))
                self.logger.debug("[debug]read new_line_str:       " + new_line_str)
                self.logger.debug("[debug]report lineno: {lineno},   line_str:       {str}".format(lineno=self.line_number, str=log_str))
                ret_dict = self.format_data_dict(log_str)
                if ret_dict is not None:
                    ret_code = report_func(self.data_id, ret_dict)
                    if not ret_code:
                        self.logger.error("report error file:{file} line:{line}".format(file=self.full_path,
                                                                                        line=line_str))
                self.line_number += 1
            else:
                self.last_line_str = new_line_str
            self.read_seek_record = self.fd.tell()

        self.no_new_data_flag = False
        if self.excepiton_regular is None:
            report(line_str)
        else:
            if self.compiled_pattern is None:
                self.compiled_pattern = re.compile(self.excepiton_regular)
            mat = re.match(self.compiled_pattern, line_str)
            if mat and mat.group():
                if re.match(self.compiled_pattern, line_str):
                    ret_str = line_str
                    for i in range(0, self.excepiton_max_lines-1):
                        next_line = self.fd.readline()
                        if next_line:
                            match = re.match(self.compiled_pattern, next_line)
                            if match and match.group():
                                ret_str += next_line
                            else:
                                report(ret_str, True)
                                report(next_line)
                                break
                        else:
                            report(line_str)
                            break
            else:
                report(line_str)

    def read_lines(self, report_func):
        cnt = 0
        try:
            if not self.open_flag:
                self.open_file()
            if self.open_flag:
                for i in range(0, self.max_read_lines_per_time):
                    line_str = self.fd.readline()
                    if line_str:
                        self.read_line_handle(line_str, report_func)
                        cnt += 1
                    else:
                        break
        except Exception, e:
            self.close_file()
            self.logger.error(traceback.format_exc())
            self.logger.error("!!!!!!!!!!!!!!!!!!!"+self.full_path)
        return cnt

    def read_moved(self, report_func):
        cnt = 0
        try:
            for i in range(0, 500):
                if i >= 100:
                    self.logger.info("too much remain log")
                    return cnt
                line_str = self.fd.readline()
                if line_str:
                    self.read_line_handle(line_str, report_func)
                    cnt += 1
                else:
                    break
            return cnt
        except Exception, e:
            self.logger.error("read removed remain log error")
            return cnt

    def __str__(self):
        return "full_path:{path}, st_ino:{st_ino}, st_dev:{st_dev}, read_seek_record:{seek}".format(
            path=self.full_path,
            st_ino=self.st_ino, st_dev=self.st_dev, seek=self.read_seek_record)


class UserLogCollector(EasyCollector):
    report_metric_info_flag = True
    component = 'custom_report'

    instance_config_folder = "/usr/local/easyops/agent/collector_agent/data/user_log_collector"
    log_read_record = {}
    record_time = 0

    agent_ip = "0.0.0.0"
    open_fd_max = 100
    opened_fd_num = 0

    def plugin_init(self):
        self.recover_from_backup()
        self.user_log_config_handler = ConifgManager(self.config["user_log_config_path"])
        self.record_time = time.time()

        self.__class__.open_fd_max = self.config["max_fd_num"]
        if not self.get_local_ip():
            exit(-1)
        return EasyCollector.plugin_init(self)

    def get_local_ip(self):
        try:
            if os.path.exists(self.config["sysconf_path"]):
                file_path = self.config["sysconf_path"]
            else:
                file_path = "/usr/local/easyops/agent/conf/sysconf.ini"
            config = ConfigParser.ConfigParser()
            config.readfp(open(file_path))
            self.__class__.agent_ip = config.get("sys", "local_ip")
            return True, ""
        except Exception, e:
            self.logger.error("read {path} error e={e}, trace={trace}".format(path=file_path, e=e,
                                                                              trace=traceback.format_exc()))
            return False, e.__str__()

    def handle_timer(self):
        # 获得采集实例
        self.last_run_time = time.time()
        self.logger.info("opened_fd_num:  {num}".format(num=self.__class__.opened_fd_num))
        self.logger.info("log_read_record length: {num}".format(num=len(self.__class__.log_read_record)))
        # 开始采集
        try:
            instances = self.get_instances()
            #self.logger.debug("%%%%%%%%%%%%%%%% {a}".format(a=instances))
            cnt = 0
            for i, instance in enumerate(instances):
                if instance.no_such_file_flag:
                    cnt += instance.read_moved(self.report_value)
                    key = (instance.full_path, instance.st_ino, instance.st_dev)
                    instance.close_file()
                    if key in self.log_read_record:
                        del self.log_read_record[key]
                else:
                    if i != len(instances):
                        instance.set_max_read_lines_per_time( (self.config["max_log_report_per_sec"]-cnt)/2 )
                    else:
                        instance.set_max_read_lines_per_time(self.config["max_log_report_per_sec"])
                    cnt += instance.read_lines(self.report_value)
                    if cnt > self.config["max_log_report_per_sec"]:
                        self.logger.info("too much log to read")
                        break
            self.logger.info("read line number: {num}".format(num=cnt))

            if time.time() - self.record_time > 60:
                for k in self.log_read_record.keys():
                    find_flag = False
                    for _, app_instances in self.instances.items():
                        for each_dict in app_instances:
                            if 'base_info' in each_dict:
                                if k == each_dict['base_info']:
                                    find_flag = True
                                    break
                    if not find_flag and time.time() - self.log_read_record[k].stopped_time > 60:
                        self.log_read_record[k].close_file()
                        del self.log_read_record[k]
                    elif self.log_read_record[k].no_new_data_flag and time.time() - self.log_read_record[k].stopped_time > 300:
                        self.log_read_record[k].report_last_line(self.report_value)
                        self.log_read_record[k].close_file()
                self.backup_read_record()
                self.record_time = time.time()
        except Exception, e:
            self.logger.error(traceback.format_exc())
        self.timecost = round(time.time() - self.last_run_time, 4)
        self.logger.info('%s run, timecost is %s' %(self.__class__.__name__, self.timecost))
        return 0

    def report_value(self, data_id, data={}):
        try:
            report_json(data_id, vals=data)
        except Exception,e:
            self.logger.error(e)
            return False
        return True

    def get_instances(self):
        time_begin = time.time()
        self.instances = self.user_log_config_handler.get_files_by_config()
        time_end = time.time()
        time_cost = time_end - time_begin
        if time_cost > 1:
            self.logger.warn("!!!!!!!!!!!config path search files cost too much time {cost}".format(cost=time_cost))

        if self.instances and len(self.instances) == 0:
            return []

        ret_instances = []
        already_delete = False
        need_to_remove = []
        #self.logger.debug("################## {a}".format(a=self.instances))
        #self.logger.debug("&&&&&&&&&&&&&&&&&& {a}".format(a=self.log_read_record))
        for app_name, file_list in self.instances.items():
            for item_dict in file_list:
                item = item_dict["base_info"]
                try:
                    log_file = os.stat(item[0])
                except Exception, e:
                    if e.__str__().find("No such file or directory") != -1:
                        already_delete = True
                        need_to_remove.append(item)
                if item in self.log_read_record:
                    file_handler = self.log_read_record[item]
                    if already_delete:
                        file_handler.no_such_file_flag = True
                        ret_instances.append(file_handler)
                        continue
                    if file_handler.st_ino == log_file.st_ino and file_handler.st_dev == log_file.st_dev:
                        if file_handler.read_seek_record < log_file.st_size:
                            ret_instances.append(file_handler)
                        else:
                            file_handler.set_no_data_flag()
                else:
                    if not already_delete:
                        app_config = self.user_log_config_handler.config_dict[app_name]
                        if app_config["start_pos"] == "begin":
                            file_handler = LogFile(item[0], log_file.st_ino, log_file.st_dev, 0, self.logger)
                        else:
                            file_handler = LogFile(item[0], log_file.st_ino, log_file.st_dev, log_file.st_size, self.logger)
                        if app_name in self.config["data_ids"]:
                            file_handler.data_id = self.config["data_ids"][app_name]
                        else:
                            file_handler.data_id = self.config["data_ids"]["default"]
                        file_handler.excepiton_regular = app_config["exception"]["regular"]
                        file_handler.excepiton_max_lines = app_config["exception"]["max_lines"]
                        file_handler.start_pos = app_config["start_pos"]
                        file_handler.app_name = app_name
                        self.log_read_record[item] = file_handler
        return ret_instances

    def backup_read_record(self):
        try:
            self.logger.info(self.config["record_file"])
            file_name = self.config["record_file"]
            tmp_dict = {}
            backup_keys = []
            for app_name, infos in self.instances.items():
                for each in infos:
                    if "base_info" in each:
                        backup_keys.append(each["base_info"])

            with open(file_name, "w") as f:
                for k, v in self.log_read_record.items():
                    if k not in backup_keys:
                        continue
                    tmp_dict[k[0]] = {
                            "st_ino": v.st_ino,
                            "st_dev": v.st_dev,
                            "read_seek_record": v.read_seek_record,
                            "full_path": v.full_path,
                            "line_number": v.line_number,
                            "data_id": v.data_id,
                            "excepiton_regular": v.excepiton_regular,
                            "excepiton_max_lines": v.excepiton_max_lines,
                            "app_name": v.app_name,
                        }
                json.dump(tmp_dict, f)
                f.flush()
        except Exception, e:
            print traceback.format_exc()
            self.logger.error(e.__unicode__())

    def recover_from_backup(self):
        try:
            file_name = self.config["record_file"]
            if os.path.exists(file_name):
                with open(file_name, "r") as f:
                    tmp_dict = json.load(f)
                    for k, v in tmp_dict.items():
                        if not os.path.isfile(v["full_path"]):
                            continue
                        key = (k, v["st_ino"], v["st_dev"])
                        self.log_read_record[key] = LogFile(v["full_path"], v["st_ino"], v["st_dev"], v["read_seek_record"], self.logger)
                        self.log_read_record[key].line_number = v["line_number"]
                        self.log_read_record[key].excepiton_regular = v["excepiton_regular"]
                        self.log_read_record[key].excepiton_max_lines = v["excepiton_max_lines"]
                        self.log_read_record[key].app_name = v["app_name"]
                        self.log_read_record[key].data_id = v["data_id"]
        except Exception,e:
            self.logger.error("init from {path} error: e".format(path=file_name, e=e))
            exit(1)


if __name__ == "__main__":
    argv = sys.argv
    if len(argv) != 3:
        exit(-1)
    if argv[1] == "test":
        t = ConifgManager(argv[2])
        ret = t.parse_config()
        if not ret:
            print "config false"
            exit(-1)
        files = t.find_files_by_patters()
        print files
