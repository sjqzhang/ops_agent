#!/usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

__author__ = 'alren'


import os
import sys
import socket
import json
import time

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
AGENT_FOLDER = os.path.dirname(os.path.dirname(CURRENT_FOLDER))
#AGENT_FOLDER = '/usr/local/easyops/agent'

sys.path.insert(0, AGENT_FOLDER)
from easyAgent.libs.report import report as agent_report
from easyAgent.libs.report_json import report as agent_report_json


def report(data_id, dims={}, vals={}, org=0):
    """
    data_id: 7001
    dims: {'test_case_id': 123}
    vals: {70011001: 'aaaa'} 或 [{70011001: 'aaaa'}]，支持一次性上报多条
    """
    #agent module
    if not isinstance(vals, (list, tuple)):
        vals_list = [vals]
    else:
        vals_list = vals
    ret = (0, '')
    for vals in vals_list:
        ret = agent_report(data_id=data_id, dims=dims, vals=vals, org=org)
        if ret[0]:
            return ret
    return ret


def report_json(data_id, dims={}, vals={}, org=0):
    if not isinstance(vals, (list, tuple)):
        vals_list = [vals]
    else:
        vals_list = vals
    ret = (0, '')
    for vals in vals_list:
        ret = agent_report_json(data_id=data_id, dims=dims, vals=vals, org=org)
        if ret[0]:
            return ret
    return ret



if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'Usage: ./report data_id msg'
        sys.exit(1)
    else:
        data_id = sys.argv[1]
        vals = {'test': sys.argv[2]}
        print report(int(data_id), vals=vals)


