#!/usr/local/easyops/python/bin/python
# encoding=utf-8

import sys
import os


if __name__ == "__main__":
    # Load framework
    framework_path = os.path.abspath(os.path.dirname(__file__)) + "/lib"
    print "\033[32mLoad framework from:\033[0m ", framework_path
    sys.path.append(framework_path)
    from easy_application import EasyApplication

    # Start service
    if len(sys.argv) >= 3:
        app = EasyApplication(sys.argv[1])
        app.process(sys.argv[2])
    else:
        print "usage: %s <conf_file> start|stop|restart" % sys.argv[0]
        sys.exit(2)
