
import socket
import struct


def ip_to_int(ip):
    return  socket.ntohl(struct.unpack("I",socket.inet_aton(ip))[0])
def int_to_ip(int_ip):
    return socket.inet_ntoa(struct.pack('I',socket.htonl(int_ip)))


if __name__ == '__main__':
    print int_to_ip(3232261135)
    print int_to_ip(3232261250)
    print int_to_ip(3232261285)
    print int_to_ip(3232261286)
    print int_to_ip(3232261320)

    print ip_to_int('192.168.100.15')
    print ip_to_int('192.168.100.137')
    print ip_to_int('192.168.100.136')
    print ip_to_int('192.168.100.138')
    print ip_to_int('192.168.100.165')
    print ip_to_int('192.168.100.166')
    print ip_to_int('192.168.100.167')
    print ip_to_int('192.168.100.173')
    print ip_to_int('192.168.100.130')
    print ip_to_int('192.168.100.109')