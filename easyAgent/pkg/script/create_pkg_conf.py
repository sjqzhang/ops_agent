#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import yaml

class folded_unicode(unicode): 
    pass
class literal_unicode(unicode): 
    pass

def folded_unicode_representer(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='>')

def literal_unicode_representer(dumper, data):
    # 经测试，如果有行尾空格的话，转换成yaml展示为多行，会变为double-quoted模式
    # 行头如果是tab分隔也会有问题
    # 不知是bug，还是规定 Alren 20160709
    data_rstrip = os.linesep.join([d.replace('\t', ' '*4).rstrip() for d in data.splitlines()])
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data_rstrip, style='|')

yaml.add_representer(folded_unicode, folded_unicode_representer)
yaml.add_representer(literal_unicode, literal_unicode_representer)

PACKAGE_CONF_SAMPLE="""
---
proc_list: []
port_list: []
start_script: ""
stop_script: ""
restart_script: ""
install_prescript: ""
install_postscript: ""
update_prescript: ""
update_postscript: ""
rollback_prescript: ""
monitor_script: ""
crontab: ""
clear_file: ""
proc_guard: none
port_guard: none
user: root:root
...
"""


def main(app_folder):
    deploy_folder=os.path.join(app_folder,"deploy")
    dst_file=os.path.join(app_folder,"package.conf.yaml")

    # 优先从deploy目录load，如果没有则从程序一级目录load，如果还没有则load模板
    if os.path.exists(os.path.join(deploy_folder, 'package.conf.yaml')):
        with open(os.path.join(deploy_folder, 'package.conf.yaml')) as fp:
            conf = yaml.load(fp)
    elif os.path.exists(os.path.join(app_folder, 'package.conf.yaml')):
        with open(os.path.join(app_folder, 'package.conf.yaml')) as fp:
            conf = yaml.load(fp)
    else:
        global PACKAGE_CONF_SAMPLE
        conf=yaml.load(PACKAGE_CONF_SAMPLE)

    section_list = [
        "install_prescript",
        "install_postscript",
        "update_postscript",
        "update_prescript",
        "start_script",
        "stop_script",
        "monitor_script",
        "crontab",
        "clear_file"
    ]
    for section in section_list:
        script_file = os.path.join(deploy_folder,section+".sh")
        if not os.path.exists(script_file):
            continue
        with open(script_file, 'r') as fp:
            conf[section] = literal_unicode(fp.read().decode('utf8'))
    # print yaml.dump(conf, default_flow_style=False)
    with open(dst_file, "w") as fp:
        yaml.dump(conf, fp, default_flow_style=False, allow_unicode=True)


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description='create package.conf.yaml')
    parser.add_argument("app_folder", help=u"the app folder")
    args = parser.parse_args()
    main(args.app_folder)

