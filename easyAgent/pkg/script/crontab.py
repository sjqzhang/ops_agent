#!/usr/local/easyops/python/bin/python
# coding=utf8
__author__ = 'leon'

'''
调用方法:
1 设置环境变量VISUAL指定crontab默认编辑器,指向crontab.py,注意要带上操作类型、包路径作为默认参数
2 指向crontab -e
3 crontab会导出配置到临时文件,并传递给VISUAL指定的编辑器,编辑器程序修改临时文件后退出,crontab自动导入变更后的临时文件

代码样例:
#! /bin/sh

op=$1
pkg=$2

if [ "$op" = "" -o "$pkg" = "" ];then
    echo "Invalid parameters"
    exit -1
fi

export VISUAL="/usr/local/easyops/agent/pkg/script/crontab.py \"$op\" \"$pkg\" "

crontab -e

'''

import sys
import yaml
import os
import common
import hashlib
import logging
import logging.handlers
import logging.config

logger = logging.getLogger("Crontab")


def init_logger():
    # log_dir = '/usr/local/easyops/pkg/easyadmin/log'
    # if not os.path.isdir(log_dir):
    #     os.makedirs(log_dir, 0o755)
    # log_file = "crontab_" + common.getUser() + ".log"
    # handler = logging.handlers.RotatingFileHandler(os.path.join(log_dir, log_file), 'a', 16*1024*1024, 2)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    global logger
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


# 获取包id
def get_pkg_id(install_path, pkg_type="pkg"):
    com = common.PkgCommon()
    pkg_info = com.getPkgId(install_path)
    if pkg_info:
        return pkg_info['packageId']
    else:
        return None

def get_pkg_config(package_id, install_path):
    pkg_real_path = os.path.realpath(install_path)
    m = hashlib.md5()
    m.update(pkg_real_path)
    instance_md5 = m.hexdigest()
    conf_file = os.path.join("/usr/local/easyops/pkg/conf", package_id, instance_md5[:7], "package.conf.yaml")
    return conf_file


class CrontabEditor:
    def __init__(self, pakcage_path, package_id, cron_file):
        self.package_path = pakcage_path
        self.package_id = package_id
        self.cron_file = cron_file
        self.sys_cron = None
        self.pkg_cron = None
        self.pkg_conf = None
        self.lock = None
        global logger
        self.logger = logger

    def read_cron(self):
        try:
            with open(self.cron_file, 'r') as f:
                self.sys_cron = f.read()
            return 0
        except Exception, e:
            self.logger.error("Read cron file failed: %s", e.__str__())
            return 10

    def write_cron(self):
        try:
            with open(self.cron_file, "w") as f:
                f.write(self.sys_cron)
            return 0
        except Exception, e:
            self.logger.error("Write cron file failed: %s", e.__str__())
            return 11

    def get_cron_task(self):
        if self.pkg_conf is None:
            self.pkg_conf = get_pkg_config(self.package_id, self.package_path)

        self.pkg_cron = common.getConfig(self.pkg_conf, 'crontab')

        if self.pkg_cron == "":
            return 0

        return 0

    def edit_cron(self, op):
        if self.sys_cron is None:
            ret = self.read_cron()
            if ret != 0:
                return ret

        if self.pkg_cron is None:
            ret = self.get_cron_task()
            if ret != 0:
                return ret

        cnt = 0
        if op == "add":
            cnt = self.add_cron()
        elif op == "del":
            cnt = self.del_cron()

        #if cnt == 0:
        #    return False

        return self.write_cron()

    def add_cron(self):
        cnt = 0
        for line in self.pkg_cron.split("\n"):
            exist, pos = self.is_conf_exist(line)
            if len(line) == 0 or exist:
                # 配置已存在
                continue
            if len(self.sys_cron) == 0:
                self.sys_cron = line + "\n"
            elif self.sys_cron[-1] == "\n":
                self.sys_cron += line + "\n"
            else:
                self.sys_cron += "\n" + line + "\n"
            cnt += 1
            self.logger.info("Add\t%s", line)

        return cnt

    def del_cron(self):
        cnt = 0
        for line in self.pkg_cron.split("\n"):
            # 加入循环控制用于删除多条重复记录
            while True:
                exist, pos = self.is_conf_exist(line)
                if len(line) == 0 or not exist:
                    # 配置不存在
                    break
                # 删除配置
                part1 = self.sys_cron[0:pos]
                part2 = self.sys_cron[pos+len(line):]
                if len(part2) > 0 and part2[0] == "\n":
                    self.sys_cron = part1 + part2[1:]
                else:
                    self.sys_cron = part1 + part2
                cnt += 1
                self.logger.info("Del\t%s", line)

        return cnt

    def is_conf_exist(self, conf):
        total_len = len(self.sys_cron)
        conf_len = len(conf)

        start = 0
        # 循环查找所有匹配项
        while start < total_len and conf_len > 0:
            pos = self.sys_cron.find(conf, start)
            if pos == -1:
                return False, -1

            head = False
            tail = False

            # 判断匹配到的是否是行首
            if pos == 0 or self.sys_cron[pos-1] == "\n":
                head = True

            # 判断匹配到的是否是行尾
            if pos+conf_len == total_len or self.sys_cron[pos+conf_len] == "\n":
                tail = True

            if head and tail:
                return True, pos

            # 调整偏移量,继续匹配余下字符串
            start = pos + conf_len

        return False, -1


if __name__ == '__main__':
    init_logger()

    # 获取参数
    if len(sys.argv) != 4:
        logger.error("Invalid parameters")
        exit(1)

    op = sys.argv[1]
    if op not in ['add', 'del']:
        logger.error("Invalid operation: %s", op)
        exit(1)

    pkg_path = sys.argv[2]
    if not os.path.isdir(pkg_path):
        logger.error("Invalid package path: %s", pkg_path)
        exit(0)

    cron_file = sys.argv[3]
    if not os.path.isfile(cron_file):
        logger.error("Invalid cron config: %s", cron_file)
        exit(1)

    pkg_id = get_pkg_id(pkg_path)
    if pkg_id is None:
        logger.error("Invalid package path: %s", pkg_path)
        exit(2)

    cron_editor = CrontabEditor(pkg_path, pkg_id, cron_file)

    ret = cron_editor.edit_cron(op)
    exit(ret)
