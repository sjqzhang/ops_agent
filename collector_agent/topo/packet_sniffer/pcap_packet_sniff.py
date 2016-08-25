#-*- coding: utf-8 -*-
__author__ = 'hzp'

pcap_failed = False
try:
    import pcap
except Exception, e:
    pcap_failed = True

import dpkt
import socket
import time

import topo.packet_sniffer.packet_sniff


class PcapPacketSniff(topo.packet_sniffer.packet_sniff.PacketSniff):
    def __init__(self, logger):
        topo.packet_sniffer.packet_sniff.PacketSniff.__init__(self, logger)

    def sniff(self, count, timeout):
        """
        抓包方法
        :param count: 抓包数量
        :param timeout: 抓包时间
        :return: [(nano_ts, type(tcp or udp), src_ip, src_port, dst_ip, dst_port, length, syn), ...]
        """
        global pcap_failed
        if pcap_failed:
            self._logger.error("pcap import failed!!!!")
            return None

        start_time = time.time()
        packets = []
        sniffer = pcap.pcap(name=None, promisc=False, immediate=True, snaplen=100, timeout_ms=timeout*1000)
        sniffer.setfilter("tcp or udp")
        try:
            for ts, raw_buf in sniffer:
                if count % 1000 == 0:
                    time.sleep(1)
                try:
                    # Unpack the Ethernet frame (mac src/dst, ethertype)
                    eth = dpkt.ethernet.Ethernet(raw_buf)
                    ip_data = eth.data
                    tcp_data = ip_data.data

                    src_ip = socket.inet_ntoa(ip_data.src)
                    src_port = tcp_data.sport
                    dst_ip = socket.inet_ntoa(ip_data.dst)
                    dst_port = tcp_data.dport
                    length = ip_data.len
                    syn = False
                    if type(tcp_data) == dpkt.udp.UDP:
                        packet_type = "udp"
                    else:
                        packet_type = "tcp"
                        syn_flag = (tcp_data.flags & dpkt.tcp.TH_SYN) != 0
                        ack_flag = (tcp_data.flags & dpkt.tcp.TH_ACK) != 0
                        if syn_flag and not ack_flag:
                            syn = True

                    packets.append((ts, packet_type, src_ip, src_port, dst_ip, dst_port, length, syn))

                    count -= 1
                    if count == 0:
                        break
                    if time.time() - start_time > timeout:
                        break
                except Exception, e:
                    self._logger.error("pcap failed, e={}".format(e))
                    continue
        except Exception, e:
            #timeout
            pass

        self._logger.debug("packets: {}".format(packets))
        return packets

