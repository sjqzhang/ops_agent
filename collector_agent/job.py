#! /usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import os
import sys
path = os.path.dirname(os.path.abspath(__file__))
collector_agent_path = path
lib_path = os.path.join(os.path.dirname(path), 'easy_framework/lib')
COLLECTOR_PATH = os.path.join(collector_agent_path, 'collector')
sys.path.append(path)
sys.path.append(lib_path)
sys.path.append(collector_agent_path)
sys.path.append(COLLECTOR_PATH)

import imp
import copy
import logging
import traceback
import json
import yaml
import fcntl

from cloghandler import ConcurrentRotatingFileHandler

DEFAULT_CONF_PATH = os.path.join(path, 'data')
COLLECTOR_PLUGIN_CONF = os.path.join(path, 'conf/collector.yaml')
SYNC_FILE = os.path.join(DEFAULT_CONF_PATH, 'sync.update.lock')

if not os.path.exists(DEFAULT_CONF_PATH):
    os.makedirs(DEFAULT_CONF_PATH, 0o755)

def get_logger():
    logger = logging.getLogger('job')
    log_format = '%(asctime)s %(filename)s %(lineno)d %(levelname)s %(message)s'
    formatter = logging.Formatter(log_format)
    logfile = os.path.join(collector_agent_path, 'log/job.log')
    rotate_handler = ConcurrentRotatingFileHandler(logfile, "a", 2000000, 7)
    rotate_handler.setFormatter(formatter)
    logger.addHandler(rotate_handler)
    logger.setLevel(logging.DEBUG)
    return logger


logger = get_logger()


class CCWorker:
    def __init__(self, conf_path):
        self.conf_path = conf_path

    def init_component_conf(self, plugin):
        plugin_conf = {
            'name': '%s_collector' % plugin.get('name', ''),
            'config': plugin.get('kwargs', {}),
        }

        logger.debug('init_component_conf: %s' % plugin_conf)
        return plugin_conf

    def get_current_config_name(self):
        files = os.listdir(DEFAULT_CONF_PATH)
        names = []
        for f in files:
            if f.endswith('.json'):
                names.append(f[:-5])
        return names

    def sync(self, plugins):
        fd = open(SYNC_FILE, 'w')
        fcntl.lockf(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info('sync start...')

        sync_names = []
        for plugin in plugins:
            collector_conf = self.init_component_conf(plugin)
            collector_name = collector_conf['name']
            conf_file = os.path.join(self.conf_path, '%s.json' % collector_name)
            sync_names.append(collector_name)

            conf = {}
            if collector_conf['config']:
                conf[collector_name] = collector_conf['config']
            self.write(conf, conf_file)

        current_names = self.get_current_config_name()
        diff_names = list(set(current_names) - set(sync_names))
        for name in diff_names:
            conf_file = os.path.join(self.conf_path, '%s.json' % name)
            self.write({}, conf_file)

        logger.info('sync rewrite `%s`' % sync_names)
        if diff_names:
            logger.info('sync remove `%s`' % diff_names)

        fcntl.lockf(fd.fileno(), fcntl.LOCK_UN)
        fd.close()

        return True

    def update(self, collector_plugin, disabled=False):
        component = collector_plugin['name']
        conf_file = os.path.join(self.conf_path, '%s.json' % component)
        lock_file = '%s.lock' % conf_file
        fd = open(lock_file, 'w')
        fcntl.lockf(fd.fileno(), fcntl.LOCK_EX)

        conf = self.read(conf_file)
        instances = conf.pop(component, [])

        config = collector_plugin['config']
        if 'host' in config and 'port' in config:
            instances = [ obj for obj in instances
                    if obj.get('host') != config['host'] or obj.get('port') != config['port'] ]

        if not disabled and config:
            instances.append(config)
        if instances:
            conf[component] = instances

        self.write(conf, conf_file)

        fcntl.lockf(fd.fileno(), fcntl.LOCK_UN)
        fd.close()

        return True

    def get_config_plugins(self):
        collector_plugin_conf = []

        if os.path.exists(COLLECTOR_PLUGIN_CONF):
            config = {}
            with open(COLLECTOR_PLUGIN_CONF) as f:
                config = yaml.load(f.read())
            if isinstance(config, dict):
                collector_plugin_conf = config.get('plugins', [])

        return collector_plugin_conf

    def is_plugin_disabled(self, plugin_name):
        res = True
        collector_plugin_conf = self.get_config_plugins()
        plugin_conf = filter(lambda x: x['name'] == plugin_name, collector_plugin_conf)

        if plugin_conf:
            config = plugin_conf[0].get('config')
            if config:
                res = config.get('disabled', False)
            else:
                res = False

        return res

    def validate(self, plugin):
        '''return (code, msg), code is 0 if plugin is valid
        '''
        try:
            plugin_name = plugin['name']
            plugin_path = COLLECTOR_PATH
            plugin_conf = plugin['config']
            plugin_class = ''.join(x.capitalize() for x in plugin_name.split('_'))

            module = imp.load_module(plugin_class, *imp.find_module(plugin_name, [plugin_path]))
        except Exception as e:
            logger.error('Import plugin module failed: %s' % traceback.format_exc())
            return 1, e.message or unicode(e)
        else:
            try:
                if self.is_plugin_disabled(plugin_name):
                    return 1, 'plugin `%s`, disabled' % plugin_name

                plugin_class = getattr(module, plugin_class)
                # TODO
                plugin_obj = plugin_class(self, plugin_name, None)
                plugin_obj.logger = logger
                code, msg = plugin_obj.plugin_init()

                if code:
                    return code, msg
                config = plugin_obj.fill_default_config(plugin_conf)
                return code, plugin_obj._check(config)
            except Exception as e:
                logger.error("Load plugin instance failed: %s" % traceback.format_exc())
                return 1, e.message or unicode(e)

    def read(self, conf_file):
        conf = {}
        if os.path.exists(conf_file):
            with open(conf_file, 'r') as f:
                try:
                    conf = json.loads(f.read())
                except ValueError:
                    conf = {}
        return conf

    def write(self, conf, conf_file):
        if conf:
            with open(conf_file, 'w') as f:
                f.write(json.dumps(conf, indent=4))
        else:
            if os.path.exists(conf_file):
                os.remove(conf_file)


def main(path, plugin, test=False, sync=False):
    res = {'code': 0, 'data': '', 'msg': ''}
    cc_worker = CCWorker(path)

    try:
        if sync:
            cc_worker.sync(plugin)
            return res

        component_conf = cc_worker.init_component_conf(plugin)
        code, msg = cc_worker.validate(copy.deepcopy(component_conf))

        if code:
            res['code'] = code
            res['msg'] = msg
        else:
            if not test:
                fd = open(SYNC_FILE, 'w')
                fcntl.lockf(fd.fileno(), fcntl.LOCK_EX)

                disabled = plugin.get('disabled', False)
                cc_worker.update(component_conf, disabled=disabled)

                fcntl.lockf(fd.fileno(), fcntl.LOCK_UN)
                fd.close()
            else:
                res['data'] = json.dumps(msg)
    except IOError as e:
        res['code'] = 2
        res['msg'] = 'locked by sync.update: `%s`' % (e.message or unicode(e))

    return res


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('plugin', help='a dictionary like string contains the collector configuration, \
            e.g. "{\'name\': \'apache\', \'kwargs\': {\'host\': \'10.1.2.3\', \'port\': 80}}"')
    parser.add_argument('-t', '--test', action='store_true', default=False,
            help='set it as test, to test if `plugin` conf is correct which will not update component config file')
    parser.add_argument('--sync', action='store_true', default=False,
            help='set it as synchronization stage, to sync all configs of component collector \
                and the argument `plugin` should be a list')
    parser.add_argument('-p', '--path', help='collector configuration file path, default `%s`' % DEFAULT_CONF_PATH)
    args = parser.parse_args()

    res = {'code': 0, 'data': '', 'msg': ''}
    path = args.path if args.path else DEFAULT_CONF_PATH
    if not os.path.exists(path):
        logger.warn('config path `%s`, does not exist' % path)
    try:
        plugin = json.loads(args.plugin)
    except ValueError:
        res = {'code': 1, 'msg': 'args.plugin format error,should be json', 'data': ''}
    else:
        if args.sync and not isinstance(plugin, (list, tuple)):
            res = {'code': 1, 'msg': 'sync data should be iterable', 'data': ''}
        elif not args.sync and (not isinstance(plugin, dict) or not plugin):
            res = {'code': 1, 'msg': 'data should be dict and be true', 'data': ''}
        else:
            logger.info('args.plugin: %s, args.test: %s, args.sync: %s' % (plugin, args.test, args.sync))
            res = main(path, plugin, test=args.test, sync=args.sync)
            logger.info('result: %s' % res)

    print json.dumps(res)
