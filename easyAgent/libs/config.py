import imp
import commands
import inspect
import sys
import os
import yaml

sys.path.append("..")

import logging
import logging.config
import ConfigParser

_cur_path = os.path.dirname(os.path.abspath(__file__))

class AgentConfig():
    allConfig={}
    def __init__(self):
        yaml_file = os.path.join(os.path.dirname(_cur_path), "conf","conf.yaml")
        if not os.path.exists(yaml_file):
            self.allConfig = None
        else:
            self.allConfig= yaml.load(open(yaml_file))

    def get(self,L1=None,L2=None):
        if not self.allConfig:
            return None
        if L1 and L2:
            if L1 in self.allConfig and L2 in self.allConfig[L1]:
                return self.allConfig[L1][L2]
            else:
                return None
        elif L1:
            if L1 in self.allConfig:
                return self.allConfig[L1]
            else:
                return None
        else:
            return None
    def getInnerIp(self):
        inner_ip = None
        sys_conf = os.path.join(os.path.dirname(os.path.realpath(os.path.curdir)), "conf/sysconf.ini")
        if os.path.exists(sys_conf):
            conf = ConfigParser.ConfigParser()
            conf.optionxform = str
            conf.read(sys_conf)
            if (conf.has_option('sys', 'local_ip')):
                inner_ip = conf.get('sys', "local_ip")

        if not inner_ip:
            #shell = "/sbin/ip route|egrep 'src 172\.|src 10\.|src 192\.'|awk '{print $9}'|head -n 1"
            shell = "ip route|egrep 'proto kernel  scope link  src 172\.|proto kernel  scope link  src 10\.|proto kernel  scope link  src 192\.'|awk '{print $9}'|head -n 1"
            status, inner_ip = commands.getstatusoutput(shell)
        if not inner_ip:
            shell = "ip route|egrep 'proto kernel  scope link  src' |awk '{print $9}'|head -n 1"
            status, inner_ip = commands.getstatusoutput(shell)
        return inner_ip
