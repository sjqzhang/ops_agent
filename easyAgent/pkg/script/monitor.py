#!/usr/local/easyops/python/bin/python
# coding=utf8
# __author__ = 'linus'

import os
import sys
import yaml
import time
import argparse
import gevent
import random

import common
from common import catch_except
from common import PkgCommon
from easyops import pkgOp
from clear import Clear

# Todo 后面如果pkg目录位置改变，需跟随改变
AGENT_FOLDER = '/usr/local/easyops/agent'
if os.path.exists(AGENT_FOLDER):
    sys.path.append(AGENT_FOLDER)
    from easyAgent.libs.report import report
else:
    report = None
    print 'not found agent folder, will not provide process status report'

_CONF_BASE="/usr/local/easyops/pkg/conf"
class Monitor():
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
            t_list.append(gevent.spawn(self.monitorPkg, pkg_info))
        gevent.joinall(t_list)
        return 0, "ok"

    def reportStatus(self, pkg_id, pkg_conf_path, inst_info, status, err_info={}):
        reportInfo = {}
        reportInfo['dims'] = {}
        reportInfo['vals'] = {}
        reportInfo['dims']['process.process.package_id'] = pkg_id
        reportInfo['dims']['process.process.version_id'] = ""
        reportInfo['dims']['process.process.install_path'] = inst_info['installPath']

        reportInfo['vals']['process.process.package_status'] = status
        if not err_info.get('err_proc') and not err_info.get('err_port'):
            reportInfo['vals']['process.process.alert_status'] = 0
        else:
            reportInfo['vals']['process.process.alert_status'] = 1

        conf_file = os.path.join(pkg_conf_path, 'package.conf.yaml')
        proc_config = common.getConfig(conf_file, "proc_list")
        port_config = common.getConfig(conf_file, "port_list")
        proc_list = {}
        for proc in proc_config:
            proc_list[proc['proc_name']] = proc

        normal_proc_list = []
        proc_num_list = self.pkgCom.getProcNum()
        normal_proc_str = ""
        for proc_name in err_info.get('ok_proc', []):
            num_min = proc_list[proc_name].get('proc_num_min', 0)
            num_max = proc_list[proc_name].get('proc_num_max', 0)
            proc_str = "%s:%s,%s|%s" % (proc_name, num_min, num_max, proc_num_list[proc_name])
            normal_proc_list.append(proc_str)
            normal_proc_str = '##'.join(normal_proc_list)
        abnormal_proc_list = []
        abnormal_proc_str = ""
        for proc_name in err_info.get('err_proc', []):
            num_min = proc_list[proc_name].get('proc_num_min', 0)
            num_max = proc_list[proc_name].get('proc_num_max', 0)
            proc_str = "%s:%s,%s|%s" % (proc_name, num_min, num_max, proc_num_list[proc_name])
            abnormal_proc_list.append(proc_str)
            abnormal_proc_str = '##'.join(abnormal_proc_list)

        normal_port_list = []
        normal_port_str = ""
        for port in err_info.get('ok_port', []):
            normal_port_list.append(port)
        normal_port_str = "##".join(map(str, normal_port_list))

        abnormal_port_list = []
        abnormal_port_str = ""
        for port in err_info.get('err_port', []):
            abnormal_port_list.append(port)
        abnormal_port_str = "##".join(map(str, abnormal_port_list))

        reportInfo['vals']['process.process.normal_processes'] = normal_proc_str
        reportInfo['vals']['process.process.abnormal_processes'] = abnormal_proc_str
        reportInfo['vals']['process.process.normal_ports'] = normal_port_str
        reportInfo['vals']['process.process.abnormal_ports'] = abnormal_port_str
        if report:
            ret, msg = report(
                data_id = 3000,
                dims=reportInfo['dims'],
                vals=reportInfo['vals']
            )

    @catch_except# 确保不会相互影响
    def monitorPkg(self, pkg_info):
        import random
        gevent.sleep(random.randint(0, 15))

        pkg_id, pkg_conf_path, pkg_install_path = pkg_info['packageId'], pkg_info['confPath'], pkg_info['installPath']
        # 初始化log配置
        st = time.time()
        mLog = self.pkgCom.configLog(pkg_install_path, 'monitor', self.log_level)
        mLog.info('check process start: %s' %pkg_install_path)
        # 读取实例信息
        inst_conf_file = os.path.join(pkg_conf_path, 'instance.conf.yaml')
        with open(inst_conf_file, 'r') as fp:
            conf_info = yaml.load(fp)
        inst_info = conf_info.pop()

        # 检查包是否已启动
        status_conf_file = os.path.join(pkg_conf_path, 'package.status')
        if not os.path.isfile(status_conf_file):
            return 0, 'ok'
        with open(status_conf_file, 'r') as fp:
            status_info = yaml.load(fp)
        start_status = status_info['status']

        if start_status == 'stopped':
            self.reportStatus(pkg_id, pkg_conf_path, inst_info, status=start_status)
            mLog.info('package status is stopped: %s %s' %(pkg_info['installPath'], round(time.time() - st, 4)))
            return 0, 'ok'

        # 获得文件锁，准备检查。且快速失败，因为进程检查本身就是1分钟执行一次的
        ret = self.pkgCom.getLock(pkg_conf_path, timeout=10)
        if not ret:
            mLog.error("get lock error")
            return 2008, "get lock error"

        # 根据包配置信息检查包的进程状态
        conf_file = os.path.join(pkg_conf_path, 'package.conf.yaml')
        err_proc, ok_proc = self.pkgCom.checkProcStatus(conf_file, install_path=inst_info.get('installPath'))
        err_port, ok_port = self.pkgCom.checkPort(conf_file, install_path=inst_info.get('installPath'))
        proc_config = common.getConfig(conf_file, "proc_guard")
        port_config = common.getConfig(conf_file, "port_guard")
        err_info = {
            'err_proc': err_proc,
            'ok_proc': ok_proc,
            'err_port': err_port,
            'ok_port': ok_port
        }
        self.reportStatus(pkg_id, pkg_conf_path, inst_info, status=start_status, err_info=err_info)

        code = 0
        msg = 'ok'

        err_msg = ""
        if err_proc:
            err_msg += ",error process:" + ",".join(err_proc)
        if err_port:
            err_msg += ",error port:" + ",".join(map(str, err_port))

        # 包操作对象
        op = pkgOp(self.APP_BASE, inst_info['installPath'])
        if (err_proc and proc_config == 'stopStart') or (err_port and port_config == 'stopStart'):
            msg = "process error,monitor run stopStart:" + err_msg
            mLog.info(msg)
            code, msg = op.stopStart(inst_info['packageId'], inst_info['installPath'])   
        elif (err_proc and proc_config == 'custom') or (err_port and port_config == 'custom'):
            msg = "process error,monitor run custom script:" + err_msg
            mLog.info(msg)
            code, msg = op.resolve(inst_info['packageId'], inst_info['installPath'])   
        elif err_proc or err_port:
            msg = "process error,do nothing:" + err_msg
            mLog.info(msg)
        # 解锁
        self.pkgCom.unLock(pkg_conf_path)  
        mLog.info('check process end: %s %s' %(pkg_info['installPath'], round(time.time() - st, 4)))
        return code, msg

if __name__ == '__main__':
    pass
