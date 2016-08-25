# coding=utf8
import sys
import os
import pwd
import grp
import re
import argparse
import logging
import errno
import common
from common import PkgCommon
from easyops import pkgOp
import hashlib
import shutil
import yaml
import time

__author__ = 'linus'

conf_base_path = "/usr/local/easyops/pkg/conf"
agent_base_path = "/usr/local/easyops/agent"
logging.basicConfig(filename="install_pkg.log",
                    format="%(asctime)s-%(name)s-%(levelname)s-%(message)s",
                    level=logging.INFO)


def updateConf(install_path, pkg_id, version, version_id, type="pkg", file_list=[]):
    pkg_real_path = os.path.realpath(install_path)
    m = hashlib.md5()
    m.update(pkg_real_path)
    instance_md5 = m.hexdigest()
    conf_path = os.path.join(conf_base_path, pkg_id, instance_md5[:7])
    if type == "pkg":
        # copy package conf
        try:
            os.makedirs(conf_path, 0o755)
        except OSError, exc:  # Python >2.5 (except OSError, exc: for Python <2.5)
            if exc.errno == errno.EEXIST and os.path.isdir(conf_path):
                pass
            else:
                code = 1004
                msg = " create conf path error"
                return code, msg
        conf_file_name = "package.conf.yaml"
        src = os.path.join(pkg_real_path, conf_file_name)
        dst = os.path.join(conf_path, conf_file_name)
        ret = shutil.move(src, dst)

    ins_conf = {
        "packageId": pkg_id,
        "versionId": version_id,
        "versionName": version,
        "installPath": install_path,
        "installTime": time.strftime('%Y-%m-%d %H:%M:%S'),
        "packageType": type,
        "fileList": file_list,
    }
    # update version conf
    instance_conf = os.path.join(conf_path, "instance.conf.yaml")
    if not os.path.exists(instance_conf):
        pkg_conf_dir = os.path.dirname(instance_conf)
        if not os.path.exists(pkg_conf_dir):
            try:
                os.makedirs(pkg_conf_dir, 0o755)
            except OSError, exc:  # Python >2.5 (except OSError, exc: for Python <2.5)
                if exc.errno == errno.EEXIST and os.path.isdir(install_path):
                    pass
                else:
                    msg = "create conf path failed"
                    code = 1005
                    logging.error(msg)
                    return code, msg
        conf_info = []
    else:
        conf_info = yaml.load(file(instance_conf, 'r'))
    conf_info.append(ins_conf)

    with open(instance_conf, "w") as fp:
        yaml.dump(conf_info, fp)

    return 0, 'ok'


def preScript(pkg_file, user):
    instance_conf_file = os.path.join(pkg_file, "package.conf.yaml")
    code, out = common.runConfig(instance_conf_file, 'install_prescript', pkg_file, user)
    logging.info(out)
    print out
    if code != 0:
        code = 1002
        msg = "run pre script failed " + out
        logging.error(msg)
        print msg
        return code, msg
    return 0, 'ok'


def postScript(install_path, pkg_id, user):
    conf_path = getConfPath(install_path, pkg_id)
    instance_conf_file = os.path.join(conf_path, "package.conf.yaml")
    code, out = common.runConfig(instance_conf_file, 'install_postscript', install_path, user)
    if code != 0:
        code = 1002
        msg = "run post script failed " + out
        logging.error(msg)
        print msg
        return code, msg
    logging.info(out)
    print out
    return 0, 'ok'


def startApp(install_path, pkg_id, user):
    op = pkgOp(agent_base_path, install_path)
    return op.start(pkg_id, install_path)


def install(pkg_file, install_path, user, group):
    try:
        os.makedirs(install_path, 0o755)
    except OSError, exc:  # Python >2.5 (except OSError, exc: for Python <2.5)
        if exc.errno == errno.EEXIST and os.path.isdir(install_path):
            pass
        else:
            msg = " create install path error"
            code = 1001
            logging.error(msg)
            return code, msg

    cmd = "cp -rf %s/* %s/;chown %s:%s %s -R" % (pkg_file, install_path, user, group, install_path)
    code, msg = common.runShell(cmd)
    if code != 0:
        code = 1003
        msg = "install package failed " + msg + str(code)
        logging.error(msg)
        return code, msg
    return code, msg


def getFileList(path, install_path):
    file_list = []
    for root_path, dir, files in os.walk(path):
        for file in files:
            file_path = os.path.realpath(os.path.join(root_path, file))
            file_path = file_path.replace(os.path.realpath(path), os.path.realpath(install_path))
            file_list.append(file_path)
    return file_list


def checkEnv(install_path):
    global conf_base_path
    if os.path.exists(conf_base_path):
        os.chmod(conf_base_path, 0o777)
    if not os.path.exists(install_path):
        return 0, 'ok'
    if not os.path.isdir(install_path):
        code = 3001
        msg = "dst path is not a dir"
        msg = u"安装路径不是目录: '{0}'".format(install_path)
        return code, msg
    for root, dirs, files in os.walk(install_path):
        if (len(files) == 0) and (len(dirs) == 0):
            return 0, 'ok'
        else:
            code = 3002,
            msg = u"安装路径非空: '{0}'. 请指定空目录或登录对应机器后删除该目录".format(install_path)
            return code, msg


def getConfPath(install_path, pkg_id):
    pkg_real_path = os.path.realpath(install_path)
    m = hashlib.md5()
    m.update(pkg_real_path)
    instance_md5 = m.hexdigest()
    conf_path = os.path.join(conf_base_path, pkg_id, instance_md5[:7])
    return conf_path


def getPkgUser(package_path, install_path, pkg_id):
    pkg = os.path.join(package_path, "main/")
    cur_user = pwd.getpwuid(os.getuid())[0]
    cur_group = grp.getgrgid(os.getgid()).gr_name
    conf_file = os.path.join(pkg, 'package.conf.yaml')
    if not os.path.exists(conf_file):
        conf_path = getConfPath(install_path, pkg_id)
        conf_file = os.path.join(conf_path, 'package.conf.yaml')
    if not os.path.exists(conf_file):
        return cur_user, cur_group
    conf_dict = yaml.load(file(conf_file, 'r'))
    if "user" not in conf_dict:
        return cur_user, cur_group
    else:
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
        code, msg = common.runShell(shell)
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
        code, msg = common.runShell(shell)

    return user, group


def main(argv):
    packagePath = os.path.dirname(os.path.abspath(sys.argv[0]))
    parser = argparse.ArgumentParser()
    parser.add_argument("--installPath", help="install path", required=True)
    parser.add_argument("--packageId", help="package id", required=True)
    parser.add_argument("--versionName", help="version", required=True)
    parser.add_argument("--versionId", help="version id", required=True)
    parser.add_argument("--withConfig", help="with config", required=True)
    parser.add_argument("--configPackageId", help="config package id", required=False)
    parser.add_argument("--configVersionId", help="config package version id", required=False)
    parser.add_argument("--configVersionName", help="config package version name", required=False)
    parser.add_argument("--autoStart", help=" start after install", required=False, default='true')
    parser.add_argument("--simulateInstall", help=" simulate install", required=False, default='false')
    args, unknown = parser.parse_known_args()
    package = os.path.join(packagePath, "main/")
    conf = os.path.join(packagePath, "conf/")

    simulate = False
    code, msg = checkEnv(args.installPath)
    if code != 0:
        # simulate install
        if args.simulateInstall == 'true' and code == 3002:
            simulate = True
        else:
            exit_proc(code, msg)
            return

    # get user
    pkg_user, pkg_group = getPkgUser(packagePath, args.installPath, args.packageId)

    if simulate is not True:
        # install conf package to pkg
        if args.withConfig == "true":
            if os.path.exists(os.path.join(conf, "package.conf.yaml")):
                os.remove(os.path.join(conf, "package.conf.yaml"))
            code, msg = install(conf, package, pkg_user, pkg_group)
            if code != 0:
                exit_proc(code, msg)
                return
        # pre script
        code, msg = preScript(package, pkg_user)
        if code != 0:
            exit_proc(code, msg)
            return
        # install package
        code, msg = install(package, args.installPath, pkg_user, pkg_group)
        if code != 0:
            exit_proc(code, msg)
            return

    # update config package conf
    if args.withConfig == "true":
        file_list = getFileList(conf, args.installPath)
        # update config package conf
        code, msg = updateConf(args.installPath, args.configPackageId, '', args.configVersionId, type='conf', file_list=file_list)
        if code != 0:
            exit_proc(code, msg)
            return

    # update package conf
    pkg_file_list = getFileList(package, args.installPath)
    code, msg = updateConf(args.installPath, args.packageId, args.versionName, args.versionId, type='pkg', file_list=pkg_file_list)
    if code != 0:
        exit_proc(code, msg)
        return

    if simulate is not True:
        code, msg = postScript(args.installPath, args.packageId, pkg_user)
        if code != 0:
            err_msg = "文件发布成功，执行后置脚本失败。ret=%s" % (msg)
            exit_proc(code, err_msg)
            return
        start_err = 'ok'
        if args.autoStart == 'true':
            code, msg = startApp(args.installPath, args.packageId, pkg_user)
            if code != 0:
                err_msg = "文件发布成功，启动失败。ret=%s" % (msg)
                exit_proc(code, err_msg)
    else:
        msg = "模拟发布成功"

    exit_proc(0, msg)


def exit_proc(code, msg):
    if code == 0:
        out = "###result=success&code=%s&msg=%s###" % (code, msg)
        print out
        sys.exit(0)
    else:
        out = "###result=failed&code=%s&msg=%s###" % (code, msg)
        print out
        sys.exit(0)


if __name__ == '__main__':
    main(sys.argv)
