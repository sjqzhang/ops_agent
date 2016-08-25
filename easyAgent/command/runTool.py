# -*- coding: utf-8 -*-
import json
import logging
import base64
import gevent.select as gs
#import pty
import os
import time
import chardet
#import libs.easyPbV2 as pb
from gevent.subprocess import Popen, STDOUT,PIPE
from gevent import subprocess
import platform
import re
import commands

logger = logging.getLogger("logAgent")

TOOL_EXEC_OK = 120700
TOOL_EXEC_RUNNGING= 120701
TOOL_EXEC_TIMEOUT = 120702
TOOL_EXEC_FAILED = 120703
TOOL_EXEC_CODE = 120704


class runTool():
    TOOL_EXEC_OK = 120700
    TOOL_EXEC_RUNNGING= 120701
    TOOL_EXEC_TIMEOUT = 120702
    TOOL_EXEC_FAILED = 120703
    TOOL_EXEC_CODE = 120704
    def run_tool(self, easy_sock, script, **kwargs):

        execUser = kwargs.get('execUser',None)
        parser = kwargs.get('parser',None)
        scriptType = kwargs.get('scriptType',None)
        if not script:
            return 0, ""
        try:
            decode_script = base64.decodestring(script)
            #logger.info(decode_script)
        except Exception, e:
            logger.error(e)
            return (TOOL_EXEC_FAILED, str(e))

        interpreter = self.getInterpreter(parser)
        logger.info(interpreter)
        if interpreter[0] != 0:
            return interpreter[0], interpreter[2]
        parser = interpreter[1]

        env=None
        cwd="/tmp"
        if execUser:
            if platform.system() != 'Windows':
                import pwd
                try:
                    pw_record = pwd.getpwnam(execUser)
                    user_name      = pw_record.pw_name
                    user_home_dir  = pw_record.pw_dir
                    user_uid       = pw_record.pw_uid
                    user_gid       = pw_record.pw_gid
                    env = os.environ.copy()
                    env[ 'HOME' ]  = user_home_dir
                    env[ 'LOGNAME'  ]  = user_name
                    env[ 'PWD' ]  = cwd
                    env[ 'USER']  = user_name
                except Exception,e:
                    logger.error(e)
                    return (TOOL_EXEC_FAILED, u'指定用户不存在: %s' % execUser)    # tool done code
        isShell = False
        if parser is not None:
            execList = [parser,'-c',decode_script]
            #if platform.system() == 'Windows' and scriptType !='python':
            #    execList = decode_script
            #    isShell = True
        else:
            header = decode_script[:17]
            if header == "#!/usr/bin/python":
                execList = ["python", "-c", decode_script]
                isShell = False
            else:
                if platform.system() == 'Windows':
                    execList = decode_script
                    isShell = True
                else:
                    execList = ["sh", "-c", decode_script]

        #master_fd, slave_fd = pty.openpty()
        #proc = Popen(execList, shell=False, universal_newlines=True, bufsize=1,
        #             stdout=PIPE, stderr=STDOUT, env=env, cwd=cwd, close_fds=True)
        #proc = Popen(execList, shell=True, universal_newlines=True, bufsize=1,
        #             stdout=PIPE, stderr=STDOUT, env=env, cwd=cwd, close_fds=True)
        #proc = Popen(['ping', 'www.baidu.com', '-n', '3'], stdout = subprocess.PIPE)
        if platform.system() == 'Windows':
            proc = subprocess.Popen(execList,
                               shell= isShell,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE )
        else:
            import pty
            master_fd, slave_fd = pty.openpty()
            proc = Popen(execList, shell=False, universal_newlines=True, bufsize=1,
                     stdout=slave_fd, stderr=STDOUT, env=env, cwd=cwd, close_fds=True,
                         preexec_fn=self.demote(user_uid, user_gid))


        start_time = time.time()
        end_time = start_time

        timeout = .1
        last_msg = ""
        while True:
            end_time = time.time()
            if end_time - start_time > 590:
                return (TOOL_EXEC_FAILED, u'执行工具超时')

            msg = ""
            try:
                if platform.system() == 'Windows':
                    msg = proc.stdout.readline()
                    #ready, _, _ = gs.select([master_fd], [], [], timeout)
                    if msg== '' and proc.poll() != None:
                        break

                    # 如果为中文,先转换为 unicode
                    if type(msg) != unicode:
                        ret = chardet.detect(msg)
                        charset = ret['encoding']
                    if charset != 'ascii':
                        msg = msg.decode('GB2312')
                else:
                    msg = ""
                    ready, _, _ = gs.select([master_fd], [], [], timeout)
                    if ready:
                        msg = os.read(master_fd, 512)
                        logger.info(msg)

                        if len(last_msg) > 0:
                            msg = last_msg + msg
                            last_msg = ""

                        # 如果为中文,先转换为 unicode
                        if type(msg) != unicode:
                            ret = chardet.detect(msg)
                            charset = ret['encoding']
                            if charset == 'windows-1252':  # 字符串中包含单个中文字时的特殊处理
                                msg = msg.decode('utf8')
                            elif charset is not None and charset != 'ascii' and chardet != 'windows-1252':
                                msg = msg.decode(charset)
                    elif proc.poll() is not None:
                        break

                #easy_sock.send('response', response)
                easy_sock.send_response(TOOL_EXEC_RUNNGING,msg)
            except gs.error:
                logger.info('select.error continue ...')
                continue
            except UnicodeDecodeError,e:
                print e
                logger.info('UnicodeDecodeError continue ...')
                last_msg = msg
                continue
            except ValueError,e:
                print e
                logger.info('ValueError continue ...')
                last_msg = msg
                continue
            except Exception, e:
                logger.error(e)
                print e
                return (TOOL_EXEC_FAILED, u'执行任务失败, 未知原因')    # tool done code

        if platform.system() != 'Windows':
            os.close(slave_fd)
            os.close(master_fd)
        if proc.returncode == 0:
            easy_sock.send_response(TOOL_EXEC_CODE,str(proc.returncode))
            return (TOOL_EXEC_OK, "")
        else:
            easy_sock.send_response(TOOL_EXEC_CODE,str(proc.returncode))
            return (TOOL_EXEC_FAILED, "")

    def process(self, req, sock):
        para = json.loads(req.para)
        ret = (TOOL_EXEC_FAILED, "执行任务失败, 未知原因")
        cmd = para.pop('cmd',"")
        try:
            ret = self.run_tool(sock, cmd,**para)
        except Exception, e:
            logger.error(e)
        return ret
    def demote(self,user_uid, user_gid):
        def result():
            os.setgid(user_gid)
            os.setuid(user_uid)
        return result

    def getInterpreter(self, parser):
        """
        check interpreter exists or deal with #!/bin/env python
        """
        retCode = 0
        interpreter = parser
        msg = ""
        if parser in ["sh", "bash", "python", "powershell"]:  # 配合tools_service.py中的
            return retCode, interpreter, msg
        if parser.find(' ') >= 0:
            if interpreter.find("/env ") < 0:
                interpreter = parser[:parser.index(' ')]
            else:
                match = re.search('/env\s+(\w+)', interpreter)
                if match:
                    status, output = commands.getstatusoutput("which --skip-alias %s" % match.group(1))
                    if status == 0:
                        interpreter = output
                    else:
                        msg = u"找不到指定解释器: %s" % match.group(1)
                        retCode = TOOL_EXEC_FAILED
                else:
                    print "match error "
        if not os.path.exists(interpreter):
            msg = u"%s: 找不到指定解释器" % interpreter
            retCode = TOOL_EXEC_FAILED
        return retCode, interpreter, msg
