#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-
__author__ = 'linus'

import re
import os
import traceback
import base64
import hashlib
import logging
import logging.handlers
import getpass
import yaml
import gevent
from gevent import socket
from gevent.subprocess import *
import gevent.select as gs

_CONF_BASE= "/usr/local/easyops/pkg/conf"

logger = logging.getLogger("logAgent")


def getUser():
    return getpass.getuser()

def catch_except(f):
    def _deco(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception,e:
            # 这里没有logger，所以暂时先用print的方式打出
            print traceback.format_exc()
            return 1, e.message or unicode(e)
    return _deco

def chown_by_name(fpath, user, group, recursive=True):
    import pwd, grp
    try:
        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid
    except KeyError,e:
        raise ValueError('not found user or group(%s:%s)' %(user, group))
    os.chown(fpath, uid, gid)
    if recursive:
        for root, dirs, files in os.walk(fpath, followlinks=True):
            for momo in dirs:
                if not os.path.exists(os.path.join(root, momo)):
                    continue
                os.chown(os.path.join(root, momo), uid, gid)
            for momo in files:
                if not os.path.exists(os.path.join(root, momo)):
                    continue
                os.chown(os.path.join(root, momo), uid, gid)

def runShell(script, env=None, cwd="/", user=None, base64_encode=False):
    # check script
    import pwd, grp
    import pty
    
    if not script:
        return 0, ""

    try:
        # base64 decode
        if base64_encode:
            decode_script = base64.decodestring(script)
        else:
            decode_script = script

        # check user
        logger.info(decode_script)
        cur_user = pwd.getpwuid(os.getuid())[0]
        if not user or user == cur_user:
            shell_list = ["bash", "-c", decode_script.encode('utf8')]
        else:
            shell_list = ["su",  user, "-c", decode_script.encode('utf8'), "-s", "/bin/bash"]
        master_fd, slave_fd = pty.openpty()
        proc = Popen(shell_list, shell=False, universal_newlines=True, bufsize=1,
                     stdout=slave_fd, stderr=STDOUT, env=env, cwd=cwd, close_fds=True)
    except Exception, e:
        logger.error(e)
        return (1, str(e))

    timeout = .1
    outputs = ''
    while True:
        try:
            ready, _, _ = gs.select([master_fd], [], [], timeout)
        except gs.error  as ex:
            if ex[0] == 4:
                continue
            else:
                raise
        if ready:
            data = os.read(master_fd, 512)
            outputs += data
            if not data:
                break
        elif proc.poll() is not None:
            break
    os.close(slave_fd)
    os.close(master_fd)
    proc.wait()
    status = proc.returncode
    return (status, outputs)


def getConfig(conf_file, config):
    try:
        with open(conf_file, 'r') as stream:
            conf_dict = yaml.load(stream)
            if config not in conf_dict:
                return ""
            return conf_dict[config]
    except Exception, e:
        return ""

def runConfig(conf_file, config, root_path=None, user=None):
    import pwd, grp
    if not user:
        cur_user = pwd.getpwuid(os.getuid())[0]
        conf_dict = yaml.load(file(conf_file, 'r'))
        if "user" not in conf_dict:
            user = cur_user
        else:
            if not conf_dict['user']:
                user = cur_user
            user = re.split(':', conf_dict['user'])[0]
    script = getConfig(conf_file, config)
    code, msg = runShell(script, env=None, cwd=root_path, user=user)
    return code, msg

class PkgCommon():
    proc_num_list = {}
    def __init__(self):
        global _CONF_BASE
        self.fp = {}
        self.CONF_BASE = _CONF_BASE

    def getProcNum(self):
        return self.proc_num_list

    def checkProcStatus(self,conf_path, install_path=""):
        err_app = []
        ok_app = []
        proc_config = getConfig(conf_path, "proc_list")

        #自定义监控脚本，目前自定义监控脚本如果失败则认为全部进程失败
        monitor_config = getConfig(conf_path, "monitor_script")
        if monitor_config:
            code,msg = runShell(monitor_config, cwd=install_path)
            for app_config in proc_config:
                proc_name = app_config['proc_name']
                if code:
                    err_app.append(proc_name)
                    self.proc_num_list[proc_name] = 0
                else:
                    ok_app.append(proc_name)
                    self.proc_num_list[proc_name] = 1 # 自定义监控默认为1个进程
        else:
            for app_config in proc_config:
                proc_name = app_config['proc_name']
                if app_config.get('pid_file'):
                    pid_file = app_config['pid_file']
                    pid_file = os.path.join(install_path, pid_file) # 为什么pid要是相对路径
                    if not os.path.exists(pid_file):
                        err_app.append(proc_name)
                        continue
                    else:
                        pid_list = file(pid_file).readlines()
                        for pid in pid_list:
                            shell = 'ps -p %s' % (pid)
                            code, msg = runShell(shell, cwd=install_path)
                            if code != 0 and proc_name not in err_app:
                                err_app.append(proc_name)
                                continue
                    ok_app.append(proc_name)
                else:
                    num_max = app_config.get('proc_num_max')
                    num_min = app_config.get('proc_num_min')
                    if not num_max:
                        num_max = 99999
                    if not num_min:
                        num_min = 1
                    try:
                        num_max = int(num_max)
                    except Exception as e:
                        logger.error("num_max should be unsigned integer but get '%s' " % str(num_max))
                        logger.info("num_max will use default value 99999")
                        num_max = 9999
                    try:
                        num_min = int(num_min)
                    except Exception as e:
                        logger.error("num_min should be unsigned integer but get '%s' " % str(num_min))
                        logger.info("num_min will use default value 1")
                        num_min = 1
                    shell = "ps -fC " + proc_name + "|fgrep -w " + proc_name + "| wc -l"
                    code, proc_num = runShell(shell, cwd=install_path)
                    if code != 0:
                        logger.error("proc_num should be unsigned integer but get '%s', code=%s" % (str(proc_num), str(code)))
                        err_app.append(proc_name)
                        continue
                    proc_num = int(proc_num)
                    if proc_num == 0:
                        shell = "pgrep -f '^((\S*/bin/)?(perl|python|php|sh|bash) )?(\S+/)?'" + proc_name + "'($| .+$)'|wc -l"
                        code, proc_num = runShell(shell, cwd=install_path)
                        proc_num = int(proc_num)
                        if proc_num == 0:
                            shell = "pgrep -f '^java (.*)? (\S+/)?'" + proc_name + "'($| .+$)'|wc -l"
                            code, proc_num = runShell(shell, cwd=install_path)
                            proc_num = int(proc_num)
                    self.proc_num_list[proc_name] = proc_num
                    if not (num_min <= proc_num <= num_max):
                        err_app.append(proc_name)
                    else:
                        ok_app.append(proc_name)
        return list(set(err_app)), list(set(ok_app))

    def checkPort(self,conf_path, install_path=""):
        # Todo，还不支持UDP
        port_list= getConfig(conf_path, "port_list")
        ip_list = self.getLocalIp()
        ip_list.insert(0, '127.0.0.1')
        err_port = []
        ok_port = []
        for port in port_list:
            is_open = False
            for ip in ip_list:
                is_open = self.getPortStatus(ip,port['port'])
                if is_open:
                    break
            if is_open:
                ok_port.append(port['port'])
            else:
                err_port.append(port['port'])
        return err_port, ok_port

    def getPortStatus(self,ip,port):
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            s.settimeout(3)
            s.connect((ip,int(port)))
            s.shutdown(2)
            return True
        except:
            return False

    #检查应用停止是否成功
    def checkStop(self,conf_path, install_path=""):
        ok_app, err_app, err_port, ok_port = ['default'], ['default'], ['default'], ['default']
        for i in range(15):
            gevent.sleep(2)
            if ok_app:
                err_app, ok_app = self.checkProcStatus(conf_path, install_path=install_path)
            if ok_port:
                err_port, ok_port = self.checkPort(conf_path, install_path=install_path)
            if not ok_app and not ok_port:
                break
        return ok_app, err_app, err_port, ok_port

    #检查应用启动是否成功
    def checkStart(self,conf_path, install_path=""):
        ok_app, err_app, err_port, ok_port = ['default'], ['default'], ['default'], ['default']
        for i in range(15):
            gevent.sleep(2)
            if err_app:
                err_app, ok_app = self.checkProcStatus(conf_path, install_path=install_path)
            if err_port:
                err_port, ok_port = self.checkPort(conf_path, install_path=install_path)
            if not err_app and not err_port:
                break
        return err_app, ok_app, err_port, ok_port

    def getLocalIp(self):
        import socket, fcntl, struct
        f = open('/proc/net/dev')
        if_list = []
        while True:
            line = f.readline()
            if line:
                dev_info = line.split(":")
                if len(dev_info) < 2:
                    continue;
                if_list.append(dev_info[0].strip())
            else:
                break


        ip_list = []
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for eth in if_list:
            try:
                inet = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', eth[:15]))
                ip = socket.inet_ntoa(inet[20:24])
            except Exception, e:
                continue
            ip_list.append(ip)
        return ip_list
    def getLock(self,lock_path,force=False,timeout=30,filename="easyops.lock"):
        import fcntl
        lockFile = os.path.join(lock_path,filename)
        #fp = open(lockFile,'w')
        try:
            if os.path.isfile(lockFile):
                os.chmod(lockFile, 0o777)
        except:
            pass
        self.fp[lockFile] = open(lockFile,'w')
        count = 0
        while True:
            if count > timeout:
                return False
            count += 1
            try:
                fcntl.flock(self.fp[lockFile],fcntl.LOCK_EX|fcntl.LOCK_NB)
            except IOError:
                if force == True:
                    return True
                gevent.sleep(1)
            else:
                return True
    def unLock(self,lock_path,filename="easyops.lock"):
        #fp = open(lockFile,'w')
        lockFile = os.path.join(lock_path,filename)
        self.fp[lockFile].close()
        try:
            if os.path.isfile(lockFile):
                os.chmod(lockFile, 0o777)
        except:
            pass
        return True
    # 获取包id,install_path为空时，获取所有包的id
    def getPkgList(self):
        pkg_list = {}
        if not os.path.isdir(self.CONF_BASE):
            return pkg_list
        pkg_id_list = os.listdir(self.CONF_BASE)
        for pkg in pkg_id_list:
            ins_conf_path = os.path.join(self.CONF_BASE, pkg)
            if not os.path.isdir(ins_conf_path):
                continue
            ins_paths = os.listdir(ins_conf_path)
            for ins_path in ins_paths:

                real_dir = os.path.join(ins_conf_path, ins_path)
                if not os.path.isdir(real_dir):
                    continue
                conf_file = os.path.join(real_dir, 'instance.conf.yaml')
                if not os.path.isfile(conf_file):
                    continue
                stream = file(conf_file, 'r')
                conf_infos = yaml.load(stream)
                stream.close()
                conf_info = conf_infos.pop()
                pkg_info = {
                    'packageId':conf_info['packageId'],
                    'confPath': real_dir,
                    'installPath': conf_info['installPath']
                }
                if conf_info['packageType'] in pkg_list:
                    pkg_list[conf_info['packageType']].append(pkg_info)
                else:
                    pkg_list[conf_info['packageType']] = [pkg_info]
        return pkg_list
    # 获取包id,install_path为空时，获取所有包的id
    def getPkgId(self, install_path, pkg_type="pkg"):
        pkg_info = {}
        if not os.path.isdir(self.CONF_BASE):
            return pkg_info

        #安装目录哈希值
        if install_path:
            prefix = self.getInstConfPrefix(install_path)

        pkg_list = os.listdir(self.CONF_BASE)
        for pkg in pkg_list:
            ins_conf_path = os.path.join(self.CONF_BASE, pkg)
            if not os.path.isdir(ins_conf_path):
                continue
            ins_paths = os.listdir(ins_conf_path)
            for ins_path in ins_paths:
                if prefix != ins_path:
                    continue
                real_dir = os.path.join(ins_conf_path, ins_path)
                if not os.path.isdir(real_dir):
                    continue
                conf_file = os.path.join(real_dir, 'instance.conf.yaml')
                if not os.path.isfile(conf_file):
                    continue
                stream = file(conf_file, 'r')
                conf_infos = yaml.load(stream)
                stream.close()
                conf_info = conf_infos.pop()
                if conf_info['packageType'] != pkg_type:
                    continue
                if os.path.realpath(conf_info['installPath']) == os.path.realpath(install_path):
                    pkg_info = {
                        'packageId':conf_info['packageId'],
                        'confPath': real_dir,
                        'installPath': conf_info['installPath']
                    }
                    break
            if pkg_info:
                break
        return pkg_info
    def configLog(self, install_path, log_prefix="default", level='INFO'):
        conf_info = self.getPkgId(install_path)
        if conf_info:
            pkg_id = conf_info['packageId']
            conf_path = conf_info['confPath']
        else:
            raise ValueError("%s not a valid package"%(install_path))

        log_dir = os.path.join(conf_path, 'log')
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir, 0o755)

        try:
            handler = logging.handlers.RotatingFileHandler(os.path.join(log_dir, log_prefix+".log"), 'a', 16 * 1024 * 1024, 2)
        except Exception,e:
            handler = logging.handlers.RotatingFileHandler(os.path.join("/tmp", log_prefix+".log"), 'a', 16 * 1024 * 1024, 2)

        formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)
        logger = logging.getLogger('easyops.%s.%s' %(pkg_id, log_prefix))
        logger.addHandler(handler)
        if level.upper() == 'DEBUG':
            # 如果是debug模式，则同时输出到标准输出
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        return logger
    #根据安装路径生成配置文件目录
    def getInstConfPrefix(self,install_path):
        pkg_real_path = os.path.realpath(install_path)
        m = hashlib.md5()
        m.update(pkg_real_path)
        instance_md5 = m.hexdigest()
        return instance_md5[:7]
    #根据安装路径和包id获取配置文件目录
    def getConfPath(self,install_path, pkg_id):
        instancePrefix = self.getInstConfPrefix(install_path)
        conf_path = os.path.join(self.CONF_BASE, pkg_id, instancePrefix)
        return conf_path
    def getPkgUser(self,install_path, pkg_id, package_path=""):
        import pwd, grp
        pkg = os.path.join(package_path, "main/")
        cur_user = pwd.getpwuid(os.getuid())[0]
        cur_group = grp.getgrgid(os.getgid()).gr_name
        conf_file = os.path.join(pkg, 'package.conf.yaml')
        if not os.path.exists(conf_file):
            conf_path = self.getConfPath(install_path, pkg_id)
            conf_file = os.path.join(conf_path, 'package.conf.yaml')
        if not os.path.exists(conf_file):
            return cur_user, cur_group
        conf_dict = yaml.load(file(conf_file, 'r'))
        if "user" not in conf_dict:
            return cur_user, cur_group
        else:
            if not conf_dict['user']:
                return cur_user, cur_group
            user_arr = re.split(':', conf_dict['user'])
            user = user_arr[0]
            if len(user_arr) > 1:
                group = re.split(':', conf_dict['user'])[1]
            else:
                group = user
        # check group
        exists_flag = False
        lines = file("/etc/group").readlines()
        for line in lines:
            sys_group = (re.split(':', line))[0]
            if sys_group == group:
                exists_flag = True
                break
        if not exists_flag:
            shell = '/usr/sbin/groupadd %s' % (group)
            code, msg = runShell(shell)
        # check user
        exists_flag = False
        lines = file("/etc/passwd").readlines()
        for line in lines:
            sys_user = (re.split(':', line))[0]
            if sys_user == user:
                exists_flag = True
                break
        if not exists_flag:
            shell = '/usr/sbin/useradd %s -g %s' % (user, group)
            code, msg = runShell(shell)

        return user, group

if __name__ == '__main__':
    # check = PkgCommon()
    # check.checkPort('/data/share/easyops/Agent-P/pkg/conf/83a72d11709b5dbf06868973c01e0934/42a2e8e/package.conf.yaml')
    chown_by_name('/tmp/bb', 'huangren', 'staff', True)







