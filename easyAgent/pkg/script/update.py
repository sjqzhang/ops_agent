# coding=utf8
__author__ = 'anlih'
import sys, os
import yaml
import shutil
import argparse
import hashlib
import logging
import errno
import common
from common import PkgCommon
from easyops import pkgOp
import time
import pwd, grp

logging.basicConfig(filename="update.log",
                    format="[%(asctime)s]\t%(levelname)s\tinfo:%(message)s",
                    level=logging.INFO)
conf_base_path = "/usr/local/easyops/pkg/conf"
agent_base_path = "/usr/local/easyops/agent"
public_file_list = []


def checkUpdPkg(diff_path, diff_list):
    for diff in diff_list:
        file = diff['file'].lstrip('/')
        src = os.path.join(diff_path, file)
        if diff['op'] in ["M", "A", "X"]:
            if not (os.path.isfile(src) or os.path.isdir(src)):
                msg = "file:%s download failed " % (file)
                logging.error(msg)
                code = 2003
                print code, msg
                return code, msg
            if os.path.isdir(src) or os.path.islink(src):
                continue
            src_md5 = md5File(src)
            if src_md5 != diff['newMd5']:
                msg = "file:[%s] md5 check faild,md5=%s,org md5=%s" % (
                    file, src_md5, diff['newMd5']
                )
                logging.error(msg)
                print msg
                code = 2003
                return code, msg
        else:
            continue
    return 0, 'OK'


def checkDstPkg(install_path, diff_list):
    for diff in diff_list:
        file = diff['file'].lstrip('/')
        dst = os.path.join(install_path, file)
        if diff['op'] in ["M", "D"]:
            if diff['file'] == "package.conf.yaml":
                continue
            if diff['op'] == "M" and not os.path.isfile(dst):
                msg = "file:%s not exists " % (file)
                logging.error(msg)
                code = 2003
                print code, msg
                return code, msg

            if diff['op'] == "D" and not os.path.isfile(dst):
                continue
            if os.path.isdir(dst) or os.path.islink(dst):
                continue
            dst_md5 = md5File(dst)
            if dst_md5 != diff['oldMd5']:
                msg = "file:[%s] md5 check faild,md5=%s,org md5=%s" % (
                    file, dst_md5, diff['newMd5']
                )
                logging.error(msg)
                print msg
                code = 2003
                return code, msg
        else:
            continue
    return 0, 'OK'


def md5File(file):
    m = hashlib.md5()
    fp = open(file, 'rb')
    while True:
        blk = fp.read(40960)
        if not blk:
            break
        m.update(blk)
    fp.close()
    return m.hexdigest()


def mkdir(dir):
    try:
        os.makedirs(dir, 0o755)
    except OSError, exc:  # Python >2.5 (except OSError, exc: for Python <2.5)
        if exc.errno == errno.EEXIST and os.path.isdir(dir):
            pass
        else:
            msg = " create install path error"
            code = 1001
            logging.error(msg)
            return code, msg


def updateFile(install_path, diff_path, diff_list, conf_file_list, user, group, pkg_type):
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    for diff in diff_list:
        file = diff['file'].lstrip('/')
        if pkg_type == 'conf' and file == "package.conf.yaml":
            continue
        src = os.path.join(diff_path, file)
        dst = os.path.join(install_path, file)
        if pkg_type != 'conf' and os.path.realpath(dst) in conf_file_list:
            continue
        if diff['op'] == "M":
            shutil.copy2(src, dst)
            os.chown(dst, uid, gid)
        elif diff['op'] == "A":
            public_file_list.append(file)
            if not os.path.isdir(os.path.dirname(dst)):
                mkdir(os.path.dirname(dst))
                os.chown(os.path.dirname(dst), uid, gid)
            if os.path.isdir(src):
                mkdir(dst)
                os.chown(dst, uid, gid)
            else:
                shutil.copy2(src, dst)
                os.chown(dst, uid, gid)
        elif diff['op'] == "X":
            shutil.copymode(src, dst)
        elif diff['op'] == "D":
            if file in public_file_list:
                continue
            if os.path.isfile(dst):
                os.remove(dst)
            elif os.path.isdir(dst):
                if os.path.islink(dst):
                    os.remove(dst)
                else:
                    shutil.rmtree(dst)
    return 0, 'ok'


def updateConf(install_path, package_path, pkg_id, type="pkg"):
    pkg_real_path = os.path.realpath(install_path)
    m = hashlib.md5()
    m.update(pkg_real_path)
    instance_md5 = m.hexdigest()
    conf_path = os.path.join(conf_base_path, pkg_id, instance_md5[:7])
    file_list = []
    if type == "pkg":
        # move package conf
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
        if os.path.isfile(src):
            ret = shutil.move(src, dst)
    # get version info
    filename = os.path.join(package_path, ".update.yaml")
    conf_info = yaml.load(file(filename, 'r'))
    version_id = conf_info['toVersion']
    version = ""

    if type == "conf":
        conf_file = os.path.join(conf_path, "instance.conf.yaml")
        if os.path.exists(conf_file):
            org_conf_infos = yaml.load(file(conf_file, 'r'))
            org_conf_info = org_conf_infos.pop()
            file_list = org_conf_info['fileList']
            for diff in conf_info['detail']:
                file_path = diff['file'].lstrip('/')
                dst = os.path.join(install_path, file_path)
                if diff['op'] == "D":
                    if os.path.realpath(dst) in file_list:
                        file_list.remove(os.path.realpath(dst))
                elif diff['op'] == "A":
                    if os.path.realpath(dst) not in file_list:
                        file_list.append(os.path.realpath(dst))
                else:
                    continue

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

    f = open(instance_conf, "w")
    ret = yaml.dump(conf_info, f)
    f.close()
    code = 0
    msg = 'ok'
    return code, msg


def checkPkg(install_path, package_path):
    filename = os.path.join(package_path, ".update.yaml")
    conf_info = yaml.load(file(filename, 'r'))
    code, msg = checkUpdPkg(os.path.join(package_path, "diffFiles"), conf_info['detail'])
    if code != 0:
        code = 1008
        msg = "check update pkg error " + msg
        return code, msg
    code, msg = checkDstPkg(install_path, conf_info['detail'])
    if code != 0:
        code = 202
        msg = "check dst pkg error " + msg
        return code, msg
    return code, msg


def updatePkg(install_path, package_path, conf_file_list, user, group, pkg_type='pkg'):
    filename = os.path.join(package_path, ".update.yaml")
    conf_info = yaml.load(file(filename, 'r'))
    code, msg = updateFile(install_path, os.path.join(package_path, "diffFiles"), conf_info['detail'], conf_file_list, user, group, pkg_type)
    return code, msg


def combinePkg(config_path, package_path):
    diff_path = os.path.join(config_path, "diffFiles");
    if not os.path.exists(diff_path):
        return 0, 'ok'
    for root, dirs, files in os.walk(diff_path):
        if (len(files) == 0):
            return 0, 'ok'
    cmd = "rm -f %s/diffFiles/package.conf.yaml >/dev/null 2>&1;cp -rf %s/diffFiles* %s/diffFiles" % (config_path, config_path, package_path)
    code, out = common.runShell(cmd)
    if code != 0:
        code = 1003
        msg = "combine package failed " + out
        return code, msg
    return 0, 'ok'


def getConfPkgInfo(install_path, conf_pkg_path):
    conf_base_path = "/usr/local/easyops/pkg/conf"
    file_list = []
    pkg_list = os.listdir(conf_base_path)
    for pkg in pkg_list:
        ins_conf_path = os.path.join(conf_base_path, pkg)
        if not os.path.isdir(ins_conf_path):
            continue
        ins_paths = os.listdir(ins_conf_path)
        for ins_path in ins_paths:
            real_dir = os.path.join(ins_conf_path, ins_path)
            if not os.path.isdir(real_dir):
                continue
            conf_file = os.path.join(real_dir, 'instance.conf.yaml')
            if os.path.exists(conf_file):
                stream = file(conf_file, 'r')
                conf_infos = yaml.load(stream)
                stream.close()
                conf_info = conf_infos.pop()
                if os.path.realpath(conf_info['installPath']) == os.path.realpath(install_path):
                    if conf_info['packageType'] == 'conf':
                        file_list = conf_info['fileList']

    if file_list and os.path.exists(conf_pkg_path):
        filename = os.path.join(conf_pkg_path, ".update.yaml")
        conf_info = yaml.load(file(filename, 'r'))
        for diff in conf_info['detail']:
            file_path = diff['file'].lstrip('/')
            dst = os.path.join(install_path, file_path)
            if diff['op'] == "D":
                if os.path.realpath(dst) in file_list:
                    file_list.remove(os.path.realpath(dst))
            elif diff['op'] == "A":
                if os.path.realpath(dst) not in file_list:
                    file_list.append(os.path.realpath(dst))
            else:
                continue
    return {"fileList": file_list}


def preScript(install_path, pkg_id, user):
    pkg_real_path = os.path.realpath(install_path)
    m = hashlib.md5()
    m.update(pkg_real_path)
    instance_md5 = m.hexdigest()
    conf_path = os.path.join(conf_base_path, pkg_id, instance_md5[:7])
    instance_conf_file = os.path.join(conf_path, "package.conf.yaml")
    code, out = common.runConfig(instance_conf_file, 'update_prescript', install_path, user)
    logging.error(out)
    if code != 0:
        code = 1002
        msg = "run pre script failed " + out
        logging.error(msg)
        print msg
        return code, msg
    print out
    return 0, 'ok'


def postScript(install_path, pkg_id, user):
    pkg_real_path = os.path.realpath(install_path)
    m = hashlib.md5()
    m.update(pkg_real_path)
    instance_md5 = m.hexdigest()
    conf_path = os.path.join(conf_base_path, pkg_id, instance_md5[:7])
    instance_conf_file = os.path.join(conf_path, "package.conf.yaml")
    code, out = common.runConfig(instance_conf_file, 'update_postscript', install_path, user)
    if code != 0:
        code = 1002
        msg = "run post script failed " + out
        logging.error(msg)
        print msg
        return code, msg
    logging.error(out)
    print out
    return 0, 'ok'


def start(pkg_id, install_path, user):
    op = pkgOp(agent_base_path,install_path)
    return op.start(pkg_id,install_path)

def restart(pkg_id, install_path, user):
    err = ""
    code, msg = stop(pkg_id, install_path, user)
    if code != 0:
        err = msg
    code, msg = start(pkg_id, install_path, user)
    if code != 0:
        err += msg
    if err != "":
        code = 1009
        msg = err
        return code, msg
    return 0, "ok"


def stop(pkg_id, install_path, user):
    op = pkgOp(agent_base_path,install_path)
    return op.stop(pkg_id,install_path)

def getConfigFile(pkg_id, install_path):
    pkg_real_path = os.path.realpath(install_path)
    m = hashlib.md5()
    m.update(pkg_real_path)
    instance_md5 = m.hexdigest()
    conf_path = os.path.join(conf_base_path, pkg_id, instance_md5[:7])
    conf_file = os.path.join(conf_path, "package.conf.yaml")
    return conf_file


def getPkgId(install_path):
    conf_base_path = "/usr/local/easyops/pkg/conf"
    ins_list = []
    pkg_list = os.listdir(conf_base_path)
    for pkg in pkg_list:
        ins_conf_path = os.path.join(conf_base_path, pkg)
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
            if os.path.realpath(conf_info['installPath']) == os.path.realpath(install_path):
                if conf_info['packageType'] == "conf":
                    continue
                return conf_info['packageId']
    return None


def main(argv):
    package_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    parser = argparse.ArgumentParser()
    parser.add_argument("--installPath", help="install path", required=True)
    parser.add_argument("--packageId", help="package id", required=False)
    parser.add_argument("--configPackageId", help="config package id", required=False)
    parser.add_argument("--withConfig", help="with config", required=True)
    parser.add_argument("--type", help="package type", required=False)
    parser.add_argument("--preStop", help="stop before update", required=False)
    parser.add_argument("--postRestart", help="restart after update", required=False)
    parser.add_argument("--forceUpdate", help=" update force", required=False)
    args, unknown = parser.parse_known_args()
    pkg_path = os.path.join(package_path, 'main')
    conf_pkg_path = os.path.join(package_path, 'conf')
    conf_pkg_info = getConfPkgInfo(args.installPath, conf_pkg_path)
    conf_file_list = conf_pkg_info['fileList']
    start_stop_err = ""

    #获取锁
    pkgCom = PkgCommon()
    local_conf_path = pkgCom.getConfPath(args.installPath,args.packageId)
    ret = pkgCom.getLock(local_conf_path)
    if not ret:
        exit_proc(2008, "get lock error")
    # get package id
    if args.type == "2":
        real_pkg_id = getPkgId(args.installPath)
    else:
        real_pkg_id = args.packageId
    # get user
    pkg_user, pkg_group =pkgCom.getPkgUser(args.installPath, real_pkg_id, package_path)

    # check package
    if os.path.isdir(pkg_path):
        code, msg = checkPkg(args.installPath, pkg_path)
        if code < 0:
            exit_proc(code, msg)
        elif code > 0 and args.forceUpdate != "true":
            exit_proc(code, msg)
    if os.path.isdir(conf_pkg_path):
        if os.path.exists(os.path.join(conf_pkg_path, "package.conf.yaml")):
            os.remove(os.path.join(conf_pkg_path, "package.conf.yaml"))
        code, msg = checkPkg(args.installPath, conf_pkg_path)
        if code < 0:
            exit_proc(code, msg)
        elif code > 0 and args.forceUpdate != "true":
            exit_proc(code, msg)
    # stop before update
    if args.preStop == "true":
        code, msg = stop(real_pkg_id, args.installPath, pkg_user)
        if code != 0:
            start_stop_err += msg + "\n"


    # pre script
    code, msg = preScript(args.installPath, real_pkg_id, pkg_user)
    if code != 0:
        start_stop_err += msg
        # exit_proc(code,msg)
        # return

    # do update
    if os.path.isdir(pkg_path):
        if os.path.isdir(conf_pkg_path):
            code, msg = combinePkg(conf_pkg_path, pkg_path)
            if code != 0:
                exit_proc(code, msg)
        code, msg = updatePkg(args.installPath, pkg_path, conf_file_list, pkg_user, pkg_group, 'pkg')
        if code != 0:
            exit_proc(code, msg)
    if os.path.isdir(conf_pkg_path):
        code, msg = updatePkg(args.installPath, conf_pkg_path, conf_file_list, pkg_user, pkg_group, 'conf')
        if code != 0:
            exit_proc(code, msg)

    # update config
    if os.path.isdir(pkg_path):
        code, msg = updateConf(args.installPath, pkg_path, args.packageId, 'pkg')
        if code != 0:
            exit_proc(code, msg)
    if os.path.isdir(conf_pkg_path):
        if (not args.configPackageId) and (args.type == "2"):
            args.configPackageId = args.packageId
        code, msg = updateConf(args.installPath, conf_pkg_path, args.configPackageId, 'conf')
        if code != 0:
            exit_proc(code, msg)

    # post script
    code, msg = postScript(args.installPath, real_pkg_id, pkg_user)
    if code != 0:
        exit_proc(code, msg)
        return
    if args.postRestart == "true":
        code, msg = restart(real_pkg_id, args.installPath, pkg_user)
        if code != 0:
            start_stop_err += msg
    if start_stop_err != '':
        msg = "文件升级成功，升级后重启失败，ret=%s"%(start_stop_err)
        exit_proc(1105, msg)
    exit_proc(0, 'OK')


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
