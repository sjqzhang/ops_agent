import json
import logging
from pkg.script.common import runShell

logger = logging.getLogger("logAgent")


class runCmd():
    def process(self, req,sock):
        para = json.loads(req.para)
        logger.info(para)
        ret = (1, "command execute failed!")
        try:
            ret = runShell(para['cmd'], base64_encode=True)
        except Exception, e:
            print e
            logger.error(e)
            pass
        return ret
