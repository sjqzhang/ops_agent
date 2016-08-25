# encoding=utf-8

from easy_plugin import EasyPlugin
from easy_session import EasySession

class TimerSample(EasyPlugin):

    def plugin_init(self):
        return EasyPlugin.plugin_init(self)

    def handle_timer(self):
        self._send_http_request()
        self._send_uds_request()

    def _send_http_request(self):
        session = self.app.create_session()

        code, msg = session.connect(('127.0.0.1', 5000))
        if code != 0:
            print "Connect to http server failed: ", code, msg
            return

        print "Connect http success"

        code, msg = session.send_request("Hello world!")
        if code != 0:
            print "Send http data failed: ", code, msg
            return

        print "Send http success"

        code, data = session.recv()
        if code != 0:
            print "Recv http failed: ", data

        print "Receive http: ", data

        session.close()

    def _send_uds_request(self):
        session = self.app.create_session()

        code, msg = session.connect("/tmp/unix_socket_sample", unix_socket=True)
        if code != 0:
            print "Connect to server failed: ", code, msg
            return

        print "Connect uds success"

        code, msg = session.send_request("Hello world!")
        if code != 0:
            print "Send uds data failed: ", code, msg
            return

        print "Send uds success"

        code, data = session.recv()
        if code != 0:
            print "Recv uds failed: ", data

        print "Receive uds: ", data

        session.close()
