#!/usr/local/easyops/python/bin/python
#-*- coding: utf-8 -*-
import os

from collector.jmx_collector import JmxCollector

class StormCollector(JmxCollector):
    component = 'storm'
    metric_define = {}
    allow_undefined_metric = True

        