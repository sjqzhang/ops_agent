import os
import json
import logging
import sys
import gevent
import shutil
import hashlib
import uuid
import platform
from libs import config

sys.path.append("..")
logger = logging.getLogger("logAgent")


class loadFile():
    def process(self, req, sock):
        # get info
        info = json.loads(req.para)
        logger.info(info)
        file_size = info['file_size']
        file_md5 = info['file_md5']

        # get full path
        conf = config.AgentConfig()
        prefix_path = conf.get("command", "tmp_path")
        full_path = prefix_path + info['dst_file']
        #full_path = info['dst_file']
        logger.info("loadFile(): full_path = %s" % full_path)

        # create dir
        dir_name = os.path.dirname(full_path)
        if os.path.exists(dir_name) is False:
            os.makedirs(dir_name)

        # recv then write to tmp file
        full_path_tmp = full_path + ".tmp." + str(uuid.uuid1())
        m = hashlib.md5()
        recv_len = 0
        with open(full_path_tmp, 'a+') as f:
            while recv_len < file_size:
                recv_data = None
                with gevent.Timeout(30, True):
                    code,msg = sock.recv(file_size - recv_len)
                    header,recv_data = msg
                if not recv_data:
                    print "timeout"
                    break
                else:
                    recv_len = recv_len + len(recv_data)
                    f.write(recv_data)
                    m.update(recv_data)
        recv_data_md5 = m.hexdigest()

        # check file
        if self.getFileSize(full_path_tmp) != file_size:
            return 1, "file length check error"
        if recv_data_md5 != file_md5:
            return 1, "file md5 check error"

        shutil.move(full_path_tmp, full_path)
        logger.info("loadFile(): load file OK")
        return 0, "download ok"
    def getFileSize(self,file):
        if platform.system() == 'Windows':
            file_len = 0
            with open(file, 'r') as f:
                while True:
                    d = f.read()
                    if not d:
                        break
                    file_len += len(d)
            return file_len
        else:
            return os.path.getsize(file)
