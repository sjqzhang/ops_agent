# encoding=utf-8

from easy_plugin import EasyPlugin
from easy_session import EasySession


class HttpSample(EasyPlugin):

    def plugin_init(self):
        return EasyPlugin.plugin_init(self)

    def handle_request(self, session):

        code, data = session.recv()
        if code != 0:
            print "Recv request failed: ", code, data

        code, msg = session.send_response("Got it!", EasySession.PKG_RSP_SUCC)
        if code != 0:
            print "Send response failed: ", code, msg

        session.close()
        return
