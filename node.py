import simpy
from wban_protocol_stack import *
from dqn_trainer import *

 
class Agent:
    def __init__(self, env):
        self.env = env
        self.dqn_trainer = DQNTrainer()
        self.m_sscs = BanSSCS()
        self.m_mac = BanMac()
        self.m_phy = BanPhy()
        self.m_csma_ca = CsmaCa()

        self.m_tx_pkt: Packet = None
        self.m_tx_params = BanTxParams()
        self.m_config_complete = False

        self.complete_config()

    def complete_config(self):
        if self.m_mac is None or self.m_phy is None or self.m_config_complete is True:
            return
        self.dqn_trainer.set_sscs(self.m_sscs)
        self.m_sscs.set_dqn_trainer(self.dqn_trainer)
        self.m_mac.set_sscs(self.m_sscs)
        self.m_sscs.set_mac(self.m_mac)
        self.m_mac.set_phy(self.m_phy)
        self.m_phy.set_mac(self.m_mac)
        self.m_mac.set_env(self.env)
        self.m_phy.set_env(self.env)
        self.m_sscs.set_env(self.env)
        self.dqn_trainer.set_env(self.env)

        self.m_csma_ca.set_env(self.env)
        self.m_csma_ca.set_mac(self.m_mac)
        self.m_mac.set_csma_ca(self.m_csma_ca)

        self.m_mac.do_initialize()
        self.m_phy.do_initialize()
        self.m_config_complete = True

    def set_mac(self, m_mac: BanMac):
        self.m_mac = m_mac
        self.complete_config()

    def set_phy(self, m_phy: BanPhy):
        self.m_phy = m_phy
        self.complete_config()

    def set_channel(self, m_channel: BanChannel):
        self.m_phy.set_channel(m_channel)
        self.complete_config()

    def set_device_params(self, ban_id, node_id, recipient_id):
        self.m_tx_params.ban_id = ban_id
        self.m_tx_params.node_id = node_id
        self.m_tx_params.recipient_id = recipient_id

        self.m_sscs.set_tx_params(self.m_tx_params)
        self.m_mac.set_mac_params(self.m_tx_params)

    def set_node_list(self, n_id):
        self.m_sscs.set_node_list(n_id)

    def get_mac(self):
        return self.m_mac

    def get_phy(self):
        return self.m_phy

    def get_channel(self):
        return self.m_phy.get_channel()

    def start(self, event):
        ev = self.env.event()
        ev._ok = True
        ev.callbacks.append(self.m_sscs.send_beacon)
        self.env.schedule(ev, priority=0, delay=0)


class Node:
    def __init__(self, env):
        self.env = env
        self.m_sscs = BanSSCS()
        self.m_mac = BanMac()
        self.m_phy = BanPhy()
        self.m_csma_ca = CsmaCa()

        self.m_tx_pkt: Packet = None
        self.m_tx_params = BanTxParams()
        self.m_config_complete = False

        self.complete_config()

    def complete_config(self):
        if self.m_mac is None or self.m_phy is None or self.m_config_complete is True:
            return
        self.m_mac.set_sscs(self.m_sscs)
        self.m_sscs.set_mac(self.m_mac)
        self.m_mac.set_phy(self.m_phy)
        self.m_phy.set_mac(self.m_mac)
        self.m_mac.set_env(self.env)
        self.m_phy.set_env(self.env)
        self.m_sscs.set_env(self.env)

        self.m_csma_ca.set_env(self.env)
        self.m_csma_ca.set_mac(self.m_mac)
        self.m_mac.set_csma_ca(self.m_csma_ca)

        self.m_mac.do_initialize()
        self.m_phy.do_initialize()
        self.m_config_complete = True

    def set_mac(self, m_mac: BanMac):
        self.m_mac = m_mac
        self.complete_config()

    def set_phy(self, m_phy: BanPhy):
        self.m_phy = m_phy
        self.complete_config()

    def set_channel(self, m_channel: BanChannel):
        self.m_phy.set_channel(m_channel)
        self.complete_config()

    def set_device_params(self, ban_id, node_id, recipient_id):
        self.m_tx_params.ban_id = ban_id
        self.m_tx_params.node_id = node_id
        self.m_tx_params.recipient_id = recipient_id

        self.m_sscs.set_tx_params(self.m_tx_params)
        self.m_mac.set_mac_params(self.m_tx_params)

    def get_mac(self):
        return self.m_mac

    def get_phy(self):
        return self.m_phy

    def get_channel(self):
        return self.m_phy.get_channel()

    def generate_data(self, event):
        # TODO: Generate a data packet based on a node's sampling rate
        self.m_tx_pkt = Packet(500)
        self.m_sscs.send_data(self.m_tx_pkt)

        ev = self.env.event()
        ev._ok = True
        ev.callbacks.append(self.generate_data)
        self.env.schedule(ev, priority=0, delay=0.1)
