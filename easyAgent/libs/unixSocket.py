__author__ = 'anlih'
import _socket
import os
import pwd
from gevent.server import StreamServer


def unlink(path):
    from errno import ENOENT
    try:
        os.unlink(path)
    except OSError, ex:
        if ex.errno != ENOENT:
            raise


def link(src, dest):
    from errno import ENOENT
    try:
        os.link(src, dest)
    except OSError, ex:
        if ex.errno != ENOENT:
            raise


def bind_unix_listener(path, backlog=50, user=None):
    pid = os.getpid()
    tempname = '%s.%s.tmp' % (path, pid)
    backname = '%s.%s.bak' % (path, pid)
    unlink(tempname)
    unlink(backname)
    link(path, backname)
    try:
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.setblocking(0)
        sock.bind(tempname)

        if user is not None:
            user = pwd.getpwnam(user)
            os.chown(tempname, user.pw_uid, user.pw_gid)
            os.chmod(tempname, 0600)
        sock.listen(backlog)
        try:
            os.rename(tempname, path)
        except:
            os.rename(backname, path)
            backname = None
            raise
        tempname = None
        return sock
    finally:
        unlink(backname)


if __name__ == '__main__':
    def handle(socket, address):
        ret = socket.recv(12)
        print ret


    StreamServer(bind_unix_listener('mysocket.sock'), handle).serve_forever()
