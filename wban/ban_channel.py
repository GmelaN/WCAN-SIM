from ban_seoung_sim.base.delay_model import DelayModel

from ban_seoung_sim.base.loss_model import LossModel
from ban_seoung_sim.base.packet import Packet, SpectrumSignalParameters
from ban_seoung_sim.wireless_model.prop_delay_model import PropDelayModel
from ban_seoung_sim.wireless_model.prop_loss_model import PropLossModel


class BanChannel:
    def __init__(self):
        self.m_env = None
        self.prop_loss_model: LossModel = PropLossModel()       # propagation loss model
        self.prop_delay_model: DelayModel = PropDelayModel()    # delay model
        self.path_loss_model = None                             # path loss model

        self.max_loss_db = 1.0e9
        self.m_tx_pkt: Packet | None = None
        self.m_phy_list = list()     # send a data packet to all the registered phy modules

    def add_phy_list(self, m_phy):
        self.m_phy_list.append(m_phy)
    
    def set_env(self, env):
        self.env = env

    def set_prop_loss_model(self, prop_loss_model):
        self.prop_loss_model = prop_loss_model

    def set_prop_delay_model(self, prop_delay_model):
        self.prop_delay_model = prop_delay_model

    def set_tx_pkt(self, m_tx_pkt):
        self.m_tx_pkt = m_tx_pkt

    def start_tx(self, event):
        if self.m_tx_pkt == None:
            raise Exception("Packet is not defined.")

        sender_mobility = self.m_tx_pkt.get_spectrum_tx_params().tx_phy.get_mobility()

        for receiver in self.m_phy_list:
            # if the sender is the receiver, skip the transmission
            if receiver == self.m_tx_pkt.get_spectrum_tx_params().tx_phy:
                continue

            m_tx_pkt_copy = self.m_tx_pkt.copy()

            receiver_mobility = receiver.get_mobility()
            spec_rx_params = SpectrumSignalParameters()
            spec_rx_params.duration = m_tx_pkt_copy.get_spectrum_tx_params().duration
            spec_rx_params.tx_power = m_tx_pkt_copy.get_spectrum_tx_params().tx_power
            spec_rx_params.tx_phy = m_tx_pkt_copy.get_spectrum_tx_params().tx_phy
            spec_rx_params.tx_antenna = m_tx_pkt_copy.get_spectrum_tx_params().tx_antenna

            if sender_mobility is not None and receiver_mobility is not None:
                # TODO: Calculate path loss, delay, propagation loss ... etc
                path_loss_db = self.prop_loss_model.cal_path_loss(sender_mobility, receiver_mobility)

                # print('path loss:', path_loss_db)
                # print('distance:', sender_mobility.get_distance_from(receiver_mobility.get_position()),
                #      'LOS:', sender_mobility.is_los(receiver_mobility.get_position()))

                if self.prop_delay_model is not None:
                    prop_delay = self.prop_delay_model.get_delay(sender_mobility, receiver_mobility)

                spec_rx_params.tx_power -= path_loss_db
                m_tx_pkt_copy.set_spectrum_tx_params(spec_rx_params)

                receiver.set_rx_pkt(m_tx_pkt_copy)
                # receiver.get_data_or_symbol_rate(True)

                event = self.m_env.event()
                event._ok = True
                event.callbacks.append(receiver.start_rx)
                self.m_env.schedule(event, priority=0, delay=prop_delay)

