#!/usr/local/easyops/python/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import re
import commands
import ConfigParser
import sys, os
import socket, struct, fcntl
import json
import yaml


class UnixInfo:
    '''
    collect unix information
    '''

    def __init__(self):
        self.result = {
        }
        self.cur_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    ''''get hostname'''

    def getHostName(self):
        self.result['hostname'] = socket.gethostname()

    """ get Unix Version """

    def getVersion(self):
        self.result['osVersion'] = ' '.join(os.uname()[:3])

    def getAgentVersion(self):
        try:
            yaml_file = open('../../conf/conf.yaml')
            yaml_conf = yaml.load(yaml_file)
            self.result['agentVersion'] = yaml_conf['base']['version']
        except Exception, e:
            print e

    ''' get ip mask mac  '''

    def getNetInfo(self):
        sys_conf = self.cur_path + "/../../conf/sysconf.ini"
        real_ip = ""
        if os.path.exists(sys_conf):
            conf = ConfigParser.ConfigParser()
            conf.optionxform = str
            conf.read(sys_conf)
            if (conf.has_option('sys', 'local_ip')):
                real_ip = conf.get('sys', "local_ip")

        if not real_ip:
            cmd = "/sbin/ip route|egrep 'src 172\.|src 10\.|src 192\.168'|awk '{print $9}'|head -n 1"
            status, real_ip = commands.getstatusoutput(cmd)

        cmd = "ls /sys/class/net"
        code, ifs_str = commands.getstatusoutput(cmd)
        if_list = re.split('\s+', ifs_str)
        for if_name in if_list:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', if_name[:15]))
            if_mac = ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]
            try:
                info = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('64s', if_name[:15]))
                if_ip = socket.inet_ntoa(info[20:24])
            except IOError:
                if_ip = ""
            try:
                info = fcntl.ioctl(s.fileno(), 0x891b, struct.pack('64s', if_name[:15]))
                if_mask = socket.inet_ntoa(info[20:24])
            except IOError:
                if_mask = ""
            if if_ip == real_ip:
                break
        self.result['eth0Name'] = if_name
        self.result['eth0Mask'] = if_mask
        self.result['eth0Mac'] = if_mac
        self.result['eth0Ip'] = real_ip
        self.result['ip'] = real_ip
        # default gateway
        status, gateway = commands.getstatusoutput("route | grep default|awk '{print $2}'")
        self.result['eth0DefaultGateway'] = gateway
        self.result['eth0Gateway'] = gateway
        # eth speed
        status, output = commands.getstatusoutput('ethtool ' + if_name + ' | grep \'Speed\' ')
        matches = re.search(':\s*(\d+)\w+', output)
        if matches:
            self.result['eth0Speed'] = int(matches.group(1))  # \d+Mb/s
        else:
            self.result['eth0Speed'] = 0  # \d+Mb/s

    def getIpInfo(self, if_name):
        """
        return a dict which contains ip info
        """
        ip_info = {}
        # get ip info by fcntl
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            info = fcntl.ioctl(sock.fileno(), 0x8927, struct.pack('256s', if_name[:15]))
            if_mac = ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]
        except IOError:
            if_mac = '00:00:00:00:00:00'
        try:
            info = fcntl.ioctl(sock.fileno(), 0x8915, struct.pack('64s', if_name[:15]))
            if_ip = socket.inet_ntoa(info[20:24])
        except IOError:
            if_ip = ""
        try:
            info = fcntl.ioctl(sock.fileno(), 0x891b, struct.pack('64s', if_name[:15]))
            if_mask = socket.inet_ntoa(info[20:24])
        except IOError:
            if_mask = ""
        # get speed
        if_speed = 0
        status, output = commands.getstatusoutput('ethtool ' + if_name + ' | grep \'Speed\' ')
        matches = re.search(':\s*(\d+)\w+', output)
        if matches:
            if_speed = int(matches.group(1))    # \d+Mb/s
        # get status
        if_status = "down"
        status, output = commands.getstatusoutput('ethtool ' + if_name + ' | grep \'Link\' ')
        matches = re.search('\w+ \w+: (\w+)', output)
        tmp_status = ''
        if matches:
            # get 'yes' or 'no'
            tmp_status = matches.group(1)
        if tmp_status == 'yes':
            if_status = "up"

        # store ip info
        ip_info['name'] = if_name
        ip_info['mask'] = if_mask
        ip_info['mac'] = if_mac
        ip_info['ip'] = if_ip
        ip_info['speed'] = if_speed
        ip_info['status'] = if_status
        return ip_info

    def getAllIpInfo(self):
        all_ip_info = []

        # get net card list
        cmd = "ls /sys/class/net"
        code, ifs_str = commands.getstatusoutput(cmd)
        if_list = re.split('\s+', ifs_str)
        for if_name in if_list:
            print if_name
            ip_info = self.getIpInfo(if_name)
            if ip_info['ip'] == '127.0.0.1' or len(ip_info['ip']) == 0:
                continue
            all_ip_info.append(ip_info)

        self.result['eth'] = all_ip_info


    ''' get cpu info:cpus, cpuHz by MHz'''

    def getCPUInfo(self):
        self.result['cpus'] = int(commands.getstatusoutput('cat /proc/cpuinfo |grep "processor" |wc -l')[1])

        status, output = commands.getstatusoutput('cat /proc/cpuinfo |grep "model name"|head -n 1')
        match = re.search(':\s+(.+)\s+@\s+([0-9.]+)GHz', output)
        if match:
            self.result['cpuHz'] = int(float(match.group(2)) * 1000)
            self.result['cpuModel'] = match.group(1)
        else:
            self.result['cpuHz'] = 0
            self.result['cpuModel'] = ""

    '''get Memory Size by KB'''

    def getMemInfo(self):
        code, mem_KB = commands.getstatusoutput("grep  MemTotal /proc/meminfo|awk '{print $2}'")
        self.result['memSize'] = int(mem_KB)

    ''' get Disk Size by KB'''

    def getDiskInfo(self):
        code, info = commands.getstatusoutput("fdisk -l|grep 'Disk /dev/'")
        dev_list = re.split("\n", info)
        result = 0
        for dev in dev_list:
            matches = re.search(r':\s*((\d|\.)+)\s*GB', dev)
            if matches:
                result += int(float(matches.group(1)))
        self.result['diskSize'] = result

    def sendResult(self):
        self.getHostName()
        self.getVersion()
        self.getAgentVersion()
        self.getMemInfo()
        self.getNetInfo()
        self.getAllIpInfo()
        self.getCPUInfo()
        self.getDiskInfo()
        self.result['status'] = '运营中'
        shell = "cd %s/../..;./report.py 1101 '%s' " % (self.cur_path, json.dumps(self.result))
        print shell
        ret = commands.getstatusoutput(shell)
        print ret


if __name__ == '__main__':
    u = UnixInfo()
    u.sendResult()
