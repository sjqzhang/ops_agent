#!/usr/local/easyops/python/bin/python
__author__ = 'anlih'
import sys
import os
import commands
import yaml
import json
import ConfigParser

_curPath = os.path.dirname(os.path.realpath(__file__))
_agentBasePath = os.path.dirname(os.path.dirname(_curPath))
sys.path.insert(0, _agentBasePath)

def main(argv):
    yaml_file = open(os.path.join(_agentBasePath,'conf','conf.yaml'))
    yaml_conf = yaml.load(yaml_file)
    client_id = int(yaml_conf['base']['client_id'])

    conf_base_path = "/usr/local/easyops/pkg/conf"
    ins_list = []
    if os.path.exists(conf_base_path):
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
                stream = file(conf_file, 'r')
                conf_info = yaml.load(stream)
                stream.close()
                ins_list.append(conf_info.pop())
    sys_conf = os.path.join(_agentBasePath,"conf","sysconf.ini")
    if os.path.exists(sys_conf):
        conf = ConfigParser.ConfigParser()
        conf.optionxform = str
        conf.read(sys_conf)
        if (conf.has_option('sys', 'local_ip')):
            inner_ip = conf.get('sys', "local_ip")
    else:
        inner_ip = None
    if not inner_ip:
        shell = "/sbin/ip route|egrep 'src 172\.|src 10\.|src 192\.'|awk '{print $9}'|head -n 1"
        code, inner_ip = commands.getstatusoutput(shell)
    result = {
        'deviceIp': inner_ip,
        'appId': client_id,
        'org': client_id,
        'data': ins_list,
    }

    from libs.report import report
    data_id = 12345
    msg = json.dumps(result)
    import chardet
    ret = chardet.detect(msg)
    charset = ret['encoding']
    if charset != 'ascii':
        msg = msg.decode(charset)
    vals = {data_id:msg}
    ret = report(data_id=data_id,dims={},vals=vals)
    print ret


if __name__ == '__main__':
    main(sys.argv)
