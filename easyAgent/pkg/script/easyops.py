#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
# __author__ = 'linus'

import sys
import os
import re
import pwd
import grp
import shutil
import time
import errno
import yaml
import argparse

import common
from common import catch_except
from common import PkgCommon

_CONF_BASE="/usr/local/easyops/pkg/conf"
CURR_FOLDER = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))

class pkgOp:
    def __init__(self, app_base="", install_path="", debug=False):
        global CURR_FOLDER
        self.curr_folder = CURR_FOLDER
        self.APP_BASE = app_base
        self.CONF_BASE = _CONF_BASE
        self.pkgCom = PkgCommon()
        if not install_path:
            self.install_path = os.getcwd()
        else:
            self.install_path = install_path

        pkg_info = self.pkgCom.getPkgId(self.install_path)
        if pkg_info :
            self.pkg_id = pkg_info['packageId']
            self.pkg_conf_path = pkg_info['confPath']
            log_level = 'DEBUG' if debug else 'INFO'
            self.opLog = self.pkgCom.configLog(pkg_info['installPath'],'op', log_level)
        else:
            self.pkg_id = None
            self.pkg_conf_path = None
        self.fp = {}
    def getUser(self,conf_file):
        cur_user = pwd.getpwuid(os.getuid()).pw_name
        cur_group = grp.getgrgid(os.getgid()).gr_name
        conf_dict = yaml.load(file(conf_file, 'r'))
        if not conf_dict.get('user'):
            user, group = cur_user, cur_group
        else:
            # 兼容root:root或者root.root的两种方式
            tmp = [s.strip() for s in re.split('\.|:', conf_dict['user'])]
            if len(tmp) == 1: # 如果只填了用户
                user, group = tmp[0], tmp[0]
            else:
                user, group = tmp[0:2]
        return user, group

    @catch_except
    def start(self, pkg_id, install_path, update_status=True):
        conf_file = self.getConfigFile(pkg_id, install_path)
        user, group = self.getUser(conf_file)
        # 修改文件属主
        common.chown_by_name(install_path, user, group)

        # 添加crontab
        self.opLog.info("start to add crontab")
        ret = self.pkgCom.getLock(os.path.dirname(self.CONF_BASE), filename="crontab.lock")
        if not ret:
            self.exit_proc(2005, "get lock error, please try again")
        shell = 'export VISUAL="%s/crontab.py add %s";echo "no"|crontab -e'%(self.curr_folder, install_path)
        code,msg = common.runShell(shell,user=user)
        if code != 0:
            self.exit_proc(2010, "add crontab error,code:%s,msg:%s"%(code,msg))
        ret = self.pkgCom.unLock(os.path.dirname(self.CONF_BASE), filename ="crontab.lock")
        if not ret:
            self.exit_proc(2009, "unlock error")

        # 执行启动脚本
        self.opLog.info("start to start")
        code, start_msg = common.runConfig(conf_file, "start_script", install_path)
        if code != 0:
            msg = '执行启动脚本失败, code=%s,msg=%s' % (code,start_msg)
            self.opLog.info(msg)
            return code, msg
        msg = start_msg

        self.opLog.info("start end, start to check process")
        # 检查启动结果
        err_app, ok_app, err_port, ok_port = self.pkgCom.checkStart(conf_file, install_path)

        # 更新包状态
        if update_status:
            self.opLog.info("check end,update status")
            status = {
                'status': 'started',
                'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                'successProcess': ok_app,
                'errorProcess': err_app,
                'successPort': ok_port,
                'errorPort': err_port
            }
            self.updateStatus(status)
        err_msg = ""
        if err_app or err_port:
            if err_app:
                err_msg += ",异常进程:" + ";".join(err_app)
            if err_port:
                err_msg += ",异常端口:" + ";".join(map(str, err_port))

            msg = '启动失败 %s,启动返回信息:%s' % (err_msg,start_msg)
            self.opLog.info(msg)
            code = 1009
            return code, msg
        self.opLog.info("start successfully ")
        return code, msg

    # 单独配置的启动脚本
    def restart(self, pkg_id, install_path):
        err = ""
        code, msg = self.stop(pkg_id, install_path, update_status=False)
        if code != 0:
            err = msg
        code, msg = self.start(pkg_id, install_path, update_status=True) # 考虑到本身就是stoped状态
        if code != 0:
            err += msg
        if err != "":
            code = 1009
            msg = err
            return code, msg
        return 0, "ok"

    # 通过先stop，再start来实现重启
    def stopStart(self, pkg_id, install_path):
        err = ""
        code, msg = self.stop(pkg_id, install_path)
        if code != 0:
            err = msg
        code, msg = self.start(pkg_id, install_path)
        if code != 0:
            err += msg
        if err != "":
            code = 1009
            msg = err
            return code, msg
        return 0, "ok"

    # resolve
    def resolve(self, pkg_id, install_path):
        self.opLog.info("run resolve")
        conf_file = self.getConfigFile(pkg_id, install_path)
        code, msg = common.runConfig(conf_file, "resolve_script", install_path)
        self.opLog.info("resolve end,code:%s,msg:%s" % (code, msg))
        return code, msg
        
    @catch_except
    def stop(self, pkg_id, install_path, update_status=True):
        conf_file = self.getConfigFile(pkg_id, install_path)
        user, group = self.getUser(conf_file)
        # 修改文件属主
        common.chown_by_name(install_path, user, group)

        #删除crontab
        self.opLog.info("start to clear crontab")
        ret = self.pkgCom.getLock(os.path.dirname(self.CONF_BASE), filename="crontab.lock")
        if not ret:
            self.exit_proc(2005, "get lock error, please try again")
        shell = 'export VISUAL="%s/crontab.py del %s";crontab -e'%(self.curr_folder, install_path)
        code,msg = common.runShell(shell,user=user)
        if code != 0:
            self.exit_proc(2010, "del crontab error,code:%s,msg:%s"%(code,msg))
        ret = self.pkgCom.unLock(os.path.dirname(self.CONF_BASE), filename="crontab.lock")
        if not ret:
            self.exit_proc(2009, "unlock error")

        self.opLog.info("start to stop")
        code, msg = common.runConfig(conf_file, "stop_script", install_path)
        if code != 0:
            msg = '执行停止脚本失败,code=%s,msg=%s' % (code,msg)
            self.opLog.info(msg)
            return code, msg
        self.opLog.info("stop end, start to check process")
        err_app, ok_app, ok_port, err_port = self.pkgCom.checkStop(conf_file, install_path)
        # 如果是restart的话是不更新状态的
        if update_status:
            self.opLog.info("check end,update status")
            status = {
                'status': 'stopped',
                'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                'successProcess': ok_app,
                'errorProcess': err_app,
                'successPort': ok_port,
                'errorPort': err_port
            }
            self.updateStatus(status)
        err_msg = ""
        code = 0
        if err_app or err_port:
            if err_app:
                err_msg += ",error process:" + ";".join(err_app)
            if err_port:
                err_msg += ",error port:" + ";".join(map(str, err_port))

            msg = 'stop failed %s' % (err_msg)
            code = 1010
            self.opLog.info(msg)
            return code, msg
        self.opLog.info("stop successfully")
        return code, msg

    def uninstall(self, pkg_id, install_path):
        code, msg = self.stop(pkg_id, install_path)
        back_path = "/tmp/" + pkg_id
        conf_bak_base = os.path.join(os.path.dirname(self.APP_BASE), 'confbak')
        if not os.path.exists(conf_bak_base):
            try:
                os.makedirs(conf_bak_base, 0o755)
            except OSError, exc:  # Python >2.5 (except OSError, exc: for Python <2.5)
                if exc.errno == errno.EEXIST and os.path.isdir(conf_bak_base):
                    pass
                else:
                    msg = " create bak path error"
                    code = 1001
                    print msg

        if code != 0:
            print msg
            # return code,msg
        code = 0

        # backup package
        if os.path.exists(install_path):
            back_dir = os.path.join(back_path, os.path.basename(install_path),
                                    time.strftime("%Y%m%d%H%M%S", time.localtime()))
            shutil.move(install_path, back_dir)

        # backup pakcage configfile
        conf_file = self.getConfigFile(pkg_id, install_path)
        conf_path = os.path.dirname(conf_file)
        if os.path.exists(conf_path):
            conf_bak_path = os.path.join(conf_bak_base, pkg_id)
            if not os.path.exists(conf_bak_path):
                os.makedirs(conf_bak_path, 0o755)
            shutil.move(conf_path, os.path.join(conf_bak_path, os.path.basename(conf_path) + "_" + str(time.time())))

        # backup config package configfile ,if config package exists
        pkg_info = self.pkgCom.getPkgId(install_path, 'conf')
        if pkg_info:
            conf_pkg_id = pkg_info['packageId']
            path = pkg_info['confPath']
        else:
            conf_pkg_id = None
            path = None
        if conf_pkg_id:
            conf_file = self.getConfigFile(conf_pkg_id, install_path)
            conf_path = os.path.dirname(conf_file)
            if os.path.exists(conf_path):
                conf_bak_path = os.path.join(conf_bak_base, conf_pkg_id)
                if not os.path.exists(conf_bak_path):
                    os.makedirs(conf_bak_path, 0o755)
                shutil.move(conf_path,
                            os.path.join(conf_bak_path, os.path.basename(conf_path) + "_" + str(time.time())))
        return code, msg

    # 更新包的状态
    def updateStatus(self, status):
        statusConf = os.path.join(self.pkg_conf_path, 'package.status')
        ret = yaml.dump(status, open(statusConf, 'w'), default_flow_style=False)
        return ret

    # 获取包状态
    def getStatus(self):
        statusConf = os.path.join(self.pkg_conf_path, 'status')
        status = yaml.load(open(statusConf, 'r'))
        return status

    # 获取包的配置文件
    def getConfigFile(self, pkg_id, install_path):
        conf_path = self.pkgCom.getConfPath(install_path,pkg_id)
        conf_file = os.path.join(conf_path, "package.conf.yaml")
        return conf_file

    def exit_proc(self, code, msg):
        if code == 0:
            out = "###result=success&code=%s&msg=%s###" % (code, msg)
            print out
            sys.exit(0)
        else:
            out = "###result=failed&code=%s&msg=%s###" % (code, msg)
            print out
            sys.exit(0)


    def main(self, op, options=None):
        if not self.pkg_id:
            self.exit_proc(2004, "cur path is not a valid pakage")

        ret = self.pkgCom.getLock(self.pkg_conf_path)
        if not ret:
            self.exit_proc(2005, "get lock error, please try again")

        if op == "start":
            code, msg = self.start(self.pkg_id, self.install_path)
        elif op == "stop":
            code, msg = self.stop(self.pkg_id, self.install_path)
        elif op == "restart":
            code, msg = self.restart(self.pkg_id, self.install_path)
        elif op == "uninstall":
            code, msg = self.uninstall(self.pkg_id, self.install_path)
        elif op == 'which':
            conf_path = self.pkgCom.getConfPath(self.install_path, self.pkg_id)
            print 'path is: ', conf_path
            print 'there are monitor logs, package.conf.yaml, and so on. enjoy it'
            code, msg = 0, 'success'
        self.pkgCom.unLock(self.pkg_conf_path)
        self.exit_proc(code, msg)


def init_pkg(app_folder, options=None):
    """init package config"""
    pkgCom = PkgCommon()
    if options and options.pkg_id: # 首先从参数找
        pkg_id = options.pkg_id
    else:
        pkg_info = pkgCom.getPkgId(app_folder)
        if pkg_info: # 然后尝试从pkg目录找
            pkg_id = pkg_info['packageId']
        else: # 最后取安装路径的目录名称
            _, pkg_id = os.path.split(app_folder)
            if not pkg_id:
                return 1, 'can not get app folder, install path should not "/"'
    from create_pkg_conf import main as create_conf
    create_conf(app_folder)
    from install import updateConf
    code, msg = updateConf(app_folder, pkg_id, '0.0', '0.0', type="pkg")
    if code != 0:
        return code, msg
    # 将log软链到应用目录
    conf_path = pkgCom.getConfPath(app_folder, pkg_id)
    log_admin = os.path.join(app_folder, 'log_admin')
    if os.path.islink(log_admin):
        os.unlink(log_admin)
    os.symlink(os.path.join(conf_path, 'log'), log_admin)
    return 0, 'ok'



if __name__ == '__main__':
    # 获取参数
    parser = argparse.ArgumentParser(description='control application which deploy by easyops, you should be at the app folder first')
    parser.add_argument("operation", choices=('start', 'stop', 'restart', 'uninstall', 'monitor', 'clear', 'init', 'which'), help=u'action choices')
    parser.add_argument("app_folder", nargs="?", default=None, help=u'the app folder(default: current folder)')
    parser.add_argument("--pkg_id", help=u'pkg_id for init action, you can pass packageId from CMDB(default: app folder name)')
    parser.add_argument("--debug", action='store_true', help=u'debug output')
    args = parser.parse_args()
    operation = args.operation
    app_folder = args.app_folder or os.getcwd()

    # 需要考虑安装路径被用户删除，前台界面下发卸载指令的操作
    # if not os.path.exists(app_folder):
    #     print app_folder, 'is not exits'
    #     sys.exit(1)
        
    cur_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    APP_BASE = os.path.dirname(os.path.dirname(cur_path))
    if operation == 'monitor':
        from monitor import Monitor
        m = Monitor(APP_BASE, install_path=app_folder, debug=args.debug)
        m.run()
    elif operation == 'clear':
        from clear import Clear
        c = Clear(APP_BASE, install_path=app_folder, debug=args.debug)
        c.run()
    else:
        if operation == 'init':
            code, msg = init_pkg(app_folder, args)
            if code:
                print msg
            else:
                easyops = pkgOp(APP_BASE, install_path=app_folder)
                easyops.main('which')
        else:
            easyops = pkgOp(APP_BASE, install_path=app_folder, debug=args.debug)
            easyops.main(operation)
