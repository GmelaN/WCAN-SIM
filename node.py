from ban_seoung_sim.base.packet import Packet
import simpy

from ban_seoung_sim.wban.wban_packet import WBanPacket


class Node:
    def __init__(self):
        self.env = None
        self.net_device = None
        self.m_sscs = None
        self.m_mac = None
        self.m_phy = None
        self.m_csma_ca = None

        self.m_tx_pkt: Packet | None = None
        self.m_tx_params = None

    def get_mac(self):
        return self.m_mac

    def get_phy(self):
        return self.m_phy

    def get_channel(self):
        if self.m_phy == None:
            raise Exception("you must set PHY device first.")
        return self.m_phy.get_channel()
    
    def generate_data(self, event):
        # TODO: Generate a data packet based on a node's sampling rate
        self.m_tx_pkt = WBanPacket(500)
        self.m_sscs.send_data(self.m_tx_pkt)

        ev = self.env.event()
        ev._ok = True
        ev.callbacks.append(self.generate_data)
        self.env.schedule(ev, priority=0, delay=0.1)


class NodeBuilder:
    def __init__(self):
        self.node = Node()
    
    def set_env(self, env):
        self.node.env = env
        return self

    def set_mac(self, mac):
        self.node.m_mac = mac
        return self

    def set_phy(self, phy):
        self.node.m_phy = phy
        return self

    def set_channel(self, channel):
        if self.node.m_phy == None: raise Exception("you must set PHY device first.")
        self.node.m_phy.set_channel(channel)
        return self
    
    def set_sscs(self, sscs):
        self.node.m_sscs = sscs
        return self

    def set_csma_ca(self, csma_ca):
        self.node.m_csma_ca = csma_ca
        return self
    
    def set_device_params(self, tx_params):
        self.node.m_tx_params = tx_params
        return self

    def build(self):
        if self.node.m_mac == None or self.node.m_sscs == None or self.node.m_phy == None or self.node.env == None or self.node.m_csma_ca == None:
            raise Exception("")

        self.node.m_mac.set_sscs(self.node.m_sscs)
        self.node.m_sscs.set_mac(self.node.m_mac)
        self.node.m_mac.set_phy(self.node.m_phy)
        self.node.m_phy.set_mac(self.node.m_mac)
        self.node.m_mac.set_env(self.node.env)
        self.node.m_phy.set_env(self.node.env)
        self.node.m_sscs.set_env(self.node.env)

        self.node.m_csma_ca.set_env(self.node.env)
        self.node.m_csma_ca.set_mac(self.node.m_mac)
        self.node.m_mac.set_csma_ca(self.node.m_csma_ca)

        self.node.m_mac.do_initialize()
        self.node.m_phy.do_initialize()

        return self.node
