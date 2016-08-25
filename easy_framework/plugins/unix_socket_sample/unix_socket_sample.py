__author__ = 'hzp'

from easy_plugin import EasyPlugin
from easy_session import EasySession

class UnixSocketSample(EasyPlugin):
    def handle_request(self, session):
        code, data = session.recv()
        print "uds recv data, ", code, data
        if code != 0:
            print "uds Recv request failed: ", code, data

        code, msg = session.send_response("Got it!", EasySession.PKG_RSP_SUCC)
        if code != 0:
            print "uds Send response failed: ", code, msg

        session.close()
        return