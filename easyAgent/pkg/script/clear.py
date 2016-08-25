#!/usr/local/easyops/python/bin/python
# coding=utf8
# __author__ = 'linus'
import os
import sys
import re
import time
import argparse
import gevent
import random

import common
from common import catch_except
from common import PkgCommon

_CONF_BASE="/usr/local/easyops/pkg/conf"
class Clear():
    def __init__(self, app_base, install_path=None, debug=False):
        self.APP_BASE = app_base
        self.CONF_BASE = _CONF_BASE
        self.install_path = install_path
        self.pkgCom = PkgCommon()
        self.log_level = 'DEBUG' if debug else 'INFO'

    def run(self):
        if self.install_path == 'all':
            info_list = self.pkgCom.getPkgList()
        else:
            pkg_info = self.pkgCom.getPkgId(self.install_path)
            if pkg_info:
                info_list = {'pkg': [pkg_info]}
            else:
                return 1, "%s not a valid package" %(self.install_path)

        t_list = []
        #只处理包类型为pkg的包
        if 'pkg' in info_list:
            pkg_info_list = info_list['pkg']
        else:
            pkg_info_list = []
        for pkg_info in pkg_info_list:
            t_list.append(gevent.spawn(self.clear_pkg, pkg_info))
        gevent.joinall(t_list)
        return 0, "ok"

    @catch_except
    def clear_pkg(self, pkg_info):
        gevent.sleep(random.randint(0, 15))

        pkg_id, pkg_conf_path, install_path = pkg_info['packageId'], pkg_info['confPath'], pkg_info['installPath']
        st = time.time()
        cLog = self.pkgCom.configLog(install_path, 'clear', self.log_level)
        cLog.info('clear file start: %s' %install_path)

        conf_file = os.path.join(pkg_conf_path, "package.conf.yaml")
        configs = self.get_config(conf_file)
        for config in configs:
            path = config[0]
            limit = config[1]
            cmd = config[2]
            param = config[3]
            target = config[4]
            if not os.path.isabs(path):
                path = os.path.join(install_path, path)
            if cmd == "delete":
                ret = self.delete_file(path=path, target=target, param=param, limit=limit, log=cLog)
            elif cmd == "clear":
                ret = self.clear_file(path =path , target=target, param=param, limit=limit, log=cLog)
            # todo暂未实现
            elif cmd == "tar":
                ret = self.tar_file(path =path , target=target, param=param, limit=limit, log=cLog)
            else:
                continue
        cLog.info('clear file end: %s %s' %(install_path, round(time.time() - st, 4)))
        return 0, 'ok'

    def get_config(self, config_file):
        clear_conf = common.getConfig(config_file, 'clear_file')
        # 处理以#开头的行
        regex = r"\s*#"
        conf_arr = clear_conf.splitlines()
        real_conf = []
        for line in conf_arr:
            ret = re.match(regex, line)
            if ret is None:
                # 处理#注释在行尾的情况
                reg_2 = r"^((\"[^\"]*\"|'[^']*'|[^'\"#])*)(#.*)$"
                ret = re.match(reg_2, line)
                if ret is not None:
                    conf_line = ret.group(1)
                else:
                    conf_line = line
                conf = re.split(r'\s+', conf_line)
                if len(conf) < 5:
                    continue
                real_conf.append(conf)

        return real_conf

    def delete_file(self, path, target, param, limit, log):
        code, msg = self.check_limit(path, limit)
        if code == 0:
            return code, msg
        target_reg = target.replace('*', '.*')
        if param.endswith('h'):
            limit_mtime = time.time() - int(param.strip('h')) * 3600
        elif param.endswith('m'):
            limit_mtime = time.time() - int(param.strip('m')) * 60
        elif param.endswith('d'):
            limit_mtime = time.time() - int(param.strip('d')) * 24 * 3600
        else:
            limit_mtime = time.time() - int(param) * 24 * 3600

        for root, dirs, files in os.walk(path):
            for name in files:
                filepath = os.path.join(root, name)
                if not os.path.exists(filepath):
                    continue
                mtime = os.stat(filepath).st_mtime
                if mtime < limit_mtime:
                    ret = re.match(target_reg, name)
                    if ret:
                        log.info("begin delete, file:[%s]"%(filepath))
                        try:
                            os.remove(filepath)
                            log.info("delete success, file:[%s]"%(filepath))
                        except Exception,e:
                            log.info("delete failed, file:[%s]"%(filepath))
        return 0, 'ok'

    def clear_file(self, path , target, param, limit, log):
        code, msg = self.check_limit(path, limit)
        if code == 0:
            return code, msg
        target_reg = "^%s$"%(target.replace('*', '.*'))

        if param.endswith('k'):
            param = int(param.strip('k'))
        elif param.endswith('m'):
            param = int(param.strip('m'))*1024
        elif param.endswith('g'):
            param = int(param.strip('g'))*1024*1024
        else:
            param = int(param)

        for root, dirs, files in os.walk(path):
            for name in files:
                if not re.match(target_reg, name):
                    continue
                filepath = os.path.join(root, name)
                if not os.path.exists(filepath):
                    continue
                file_size = os.stat(filepath).st_size / 1024
                if file_size > param:
                    log.info("begin clear, file:[%s]"%(filepath))
                    try:
                        with open(filepath, 'w') as fp:
                            fp.truncate()
                        log.info("clear success, file:[%s]"%(filepath))
                    except Exception,e:
                        log.info("clear failed, file:[%s]"%(filepath))

        return 0, 'ok'

    def tar_file(self, path, target, param, limit, log):
        pass

    def check_limit(self, path, limit):
        if not os.path.exists(path):
            return 0, 'ok'
        limit_config = limit.split(":")
        if len(limit_config) < 2:
            print "config error,%s" % (limit)
            return 0, 'ok'
        disk_limit = int(limit_config[0].strip("%"))
        path_limit = int(limit_config[1].strip("Mm"))
        disk = os.statvfs(path)
        disk_percent = (disk.f_blocks - disk.f_bfree) * 100 / (disk.f_blocks - disk.f_bfree + disk.f_bavail) + 1
        size = 0L
        for root, dirs, files in os.walk(path):
            for name in files:
                filepath = os.path.join(root,name)
                size += self.__calc_size(filepath)
            for name in dirs:
                filepath = os.path.join(root,name)
                size += self.__calc_size(filepath)
        path_size = size/1024  #M
        if disk_percent > disk_limit or path_size > path_limit:
            return 1, "achived limit"
        return 0, 'ok'

    def __calc_size(self, filepath):
        if not os.path.exists(filepath):
           return 0
        st = os.stat(filepath)
        if  hasattr(st,'st_blocks'):
            return st.st_blocks /2
        else:
            return st.size



if __name__ == '__main__':
    pass
