__author__ = 'hzp'

from easy_plugin import EasyPlugin

import os
import glob
import traceback


class LogFinder(EasyPlugin):
    def plugin_init(self):
        self.FILE_LIMIT = 500
        return EasyPlugin.plugin_init(self)

    def handle_timer(self):
        code, collector = self.app.get_plugin(self.config["collector_name"])
        if code != 0:
            return

        self._scan_new_files(collector)

    def _scan_new_files(self, collector):
        remove_files = []
        for file_name, file_tuple in collector.files.iteritems():
            if not os.path.exists(file_name):
                remove_files.append(file_name)
                continue

            file, st_ino, st_dev = file_tuple
            file_stat = os.stat(file_name)
            if file_stat.st_ino != st_ino or file_stat.st_dev != st_dev:
                remove_files.append(file_name)

        self.logger.debug("remove files: {0}".format(remove_files))
        for remove_file in remove_files:
            file, st_ino, st_dev = collector.files.pop(remove_file)
            file.close()

        files = glob.glob(collector.config['path'] + "/" + collector.config['pattern'])
        for file_name in files:
            if file_name not in collector.files and len(collector.files) < self.FILE_LIMIT:
                try:
                    new_file = open(file_name, "r")
                    new_file_stat = os.fstat(new_file.fileno())
                    collector.files[file_name] = (new_file, new_file_stat.st_ino, new_file_stat.st_dev)
                    new_file.seek(0, 2)
                except Exception, e:
                    self.logger.error("file operation error file: {0}, traceback:{1}".format(
                        file_name, traceback.format_exc()))

        self.logger.debug("scan_files, {0}".format(collector.files))

