from enum import Enum
import sys
from ban_seoung_sim.base.packet import Packet
from ban_seoung_sim.util.time import Time
from attr import dataclass
import numpy as np
from ban_seoung_sim.wban.wban_packet import WBanPacket
from ban_seoung_sim.wban.wban_header import AssignedLinkElement, BanFrmSubType, BanFrmType


class BanTxOption(Enum):
    TX_OPTION_NONE = 0
    TX_OPTION_ACK = 1
    TX_OPTION_GTS = 2
    TX_OPTION_INDIRECT = 3

class BanDataConfirmStatus(Enum):
    IEEE_802_15_6_SUCCESS = 0
    IEEE_802_15_6_TRANSACTION_OVERFLOW = 1
    IEEE_802_15_6_TRANSACTION_EXPIRED = 2
    IEEE_802_15_6_CHANNEL_ACCESS_FAILURE = 3
    IEEE_802_15_6_INVALID_ADDRESS = 4
    IEEE_802_15_6_INVALID_GTS = 5
    IEEE_802_15_6_NO_ACK = 6
    IEEE_802_15_6_COUNTER_ERROR = 7
    IEEE_802_15_6_FRAME_TOO_LONG = 8
    IEEE_802_15_6_UNVAILABLE_KEY = 9
    IEEE_802_15_6_UNSUPPORTED_SECURITY = 10
    IEEE_802_15_6_INVALID_PARAMETER = 11
    IEEE_802_15_6_EXCEED_ALLOCATION_INTERVAL = 12


@dataclass
class DqnStatusInfo:
    node_id = None
    current_state = None
    current_action = None
    reward = None
    next_state = None
    done = None
    steps = None


@dataclass
class BanTxParams:
    ban_id: int | None = None
    node_id: int | None = None
    recipient_id: int | None = None
    seq_num: int | None = None
    tx_option: BanTxOption | None = None


# Service specific convergence sub-layer (SSCS)
class BanSSCS:
    ACTION_SET = [- 25, -24, -23, -22, -21, -20, -18, -16, -14, -12, -10, -8, -6, -4, -2]    # dBm

    def __init__(self):
        self.m_env = None
        self.packet_list = list()
        self.m_mac = None   # To interact with a MAC layer
        self.dqn_trainer = None  # To interact with a dqn_trainer
        self.node_list = list()
        self.m_tx_params = BanTxParams()
        self.beacon_interval =  Time.milliseconds(255)  # ms
        self.m_tx_power = 0   # dBm

        self.dqn_status_info = list()

    def set_env(self, m_env):
        self.m_env = m_env

    def get_env(self):
        return self.m_env

    def set_dqn_trainer(self, dqn_trainer):
        self.dqn_trainer = dqn_trainer

    def get_dqn_trainer(self):
        return self.dqn_trainer

    def set_mac(self, m_mac):
        self.m_mac = m_mac

    def get_mac(self):
        return self.m_mac

    def set_tx_params(self, m_tx_params):
        self.m_tx_params = m_tx_params

    def set_node_list(self, n_id):
        self.node_list.append(n_id)
        self.dqn_status_info.append(self.init_dqn_status_info(n_id))

    def init_dqn_status_info(self, node_id):
        new_dqn_status = DqnStatusInfo()
        new_dqn_status.node_id = node_id
        new_dqn_status.current_state = (-80, 0)   # initial state is (Rx power, distance)
        new_dqn_status.current_action = 0
        new_dqn_status.reward = 0
        new_dqn_status.next_state = 0
        new_dqn_status.done = True
        new_dqn_status.steps = 0
        return new_dqn_status

    def data_confirm(self, status: BanDataConfirmStatus):
        # ('Time:', round(self.m_env.now, 5), '  Transmission confirm: (NID:%d),' % self.m_mac.m_mac_params.node_id,
        #      'result:', status,)
        pass

    def data_indication(self, rx_pkt: Packet):
        # data received
        rx_power = rx_pkt.get_spectrum_tx_params().tx_power
        sender_id = rx_pkt.mac_header.sender_id

        for dqn_status in self.dqn_status_info:
            if dqn_status.node_id == sender_id:
                # calculate the reward value
                if dqn_status.current_action == 0:      # -25 dBm
                    dqn_status.reward += 10
                elif dqn_status.current_action == 1:    # -24 dBm
                    dqn_status.reward += 9.5
                elif dqn_status.current_action == 2:    # -23 dBm
                    dqn_status.reward += 9
                elif dqn_status.current_action == 3:    # -22 dBm
                    dqn_status.reward += 8.5
                elif dqn_status.current_action == 4:    # -21 dBm
                    dqn_status.reward += 8
                elif dqn_status.current_action == 5:    # -20 dBm
                    dqn_status.reward += 7.5
                elif dqn_status.current_action == 6:    # -18 dBm
                    dqn_status.reward += 7
                elif dqn_status.current_action == 7:    # -16 dBm
                    dqn_status.reward += 6.5
                elif dqn_status.current_action == 8:    # -14 dBm
                    dqn_status.reward += 6
                elif dqn_status.current_action == 9:    # -12 dBm
                    dqn_status.reward += 5.5
                elif dqn_status.current_action == 10:    # -10 dBm
                    dqn_status.reward += 5
                elif dqn_status.current_action == 11:    # -8 dBm
                    dqn_status.reward += 4
                elif dqn_status.current_action == 12:    # -6 dBm
                    dqn_status.reward += 3
                elif dqn_status.current_action == 13:    # -4 dBm
                    dqn_status.reward += 2
                elif dqn_status.current_action == 14:    # -2 dBm
                    dqn_status.reward += 1
                else:
                    print('Invalid action', file=sys.stderr)

                sender_mobility = rx_pkt.get_spectrum_tx_params().tx_phy.get_mobility()
                receiver_mobility = self.m_mac.get_phy().get_mobility()

                distance = sender_mobility.get_distance_from(receiver_mobility.get_position())

                dqn_status.next_state = (rx_power, distance)
                dqn_status.done = False  # allocate Tx power to this node and successfully receive the data packet

                result = self.dqn_trainer.set_observation(dqn_status.current_state, dqn_status.current_action,
                                                          dqn_status.next_state, dqn_status.reward, dqn_status.steps,
                                                          dqn_status.done)

                # start new episode
                if result is True:
                    dqn_status.current_state = (-80, 0)  # initial state is (Rx power, distance)
                    dqn_status.current_action = 0
                    dqn_status.reward = 0
                    dqn_status.next_state = 0
                    dqn_status.done = True
                    dqn_status.steps = 0
                else:
                    dqn_status.current_state = dqn_status.next_state
                    dqn_status.steps += 1

                break

        self.packet_list.append(rx_pkt)

    def send_beacon(self, event):
        # TODO: Generate a management-type frame (beacon frame)
        m_tx_pkt = WBanPacket(10)
        m_tx_params = BanTxParams()
        m_tx_params.tx_option = BanTxOption.TX_OPTION_NONE
        m_tx_params.seq_num = None
        m_tx_params.ban_id = self.m_tx_params.ban_id
        m_tx_params.node_id = self.m_tx_params.node_id
        m_tx_params.recipient_id = 999  # broadcast id: 999

        m_tx_pkt.set_mac_header(BanFrmType.IEEE_802_15_6_MAC_MANAGEMENT,
                                BanFrmSubType.WBAN_MANAGEMENT_BEACON, m_tx_params)

        # TODO: Do the up-link scheduling
        beacon_length = self.beacon_interval * 1000  # ms
        start_offset = 0
        num_slot = 20  # for test. the number of allocation slots

        for n_index in self.node_list:
            # get the action from DQN trainer
            for dqn_status in self.dqn_status_info:
                if n_index == dqn_status.node_id:
                    action = self.dqn_trainer.get_action(dqn_status.current_state)
                    dqn_status.current_action = action
                    dqn_status.done = True
                    self.m_tx_power = BanSSCS.ACTION_SET[action]
                    break

            m_assigned_link = AssignedLinkElement()
            m_assigned_link.allocation_id = n_index
            m_assigned_link.interval_start = start_offset
            m_assigned_link.interval_end = num_slot
            m_assigned_link.tx_power = self.m_tx_power  # get the tx power (action) from the DQN
            start_offset += (num_slot + 1)
            if start_offset > beacon_length:
                break
            m_tx_pkt.get_frm_body().set_assigned_link_info(m_assigned_link)

        self.m_mac.mlme_data_request(m_tx_pkt)

        event = self.m_env.event()
        event._ok = True
        event.callbacks.append(self.beacon_interval_timeout)  # this method must be called before the send_beacon()
        event.callbacks.append(self.send_beacon)
        self.m_env.schedule(event, priority=0, delay=self.beacon_interval)

    def beacon_interval_timeout(self, event):
        # Calculate the next_state, reward, done
        for dqn_status in self.dqn_status_info:
            # if the previous resource allocation (tx power) was failed
            if dqn_status.done is True:
                dqn_status.next_state = (-85, -1)  # Rx power beyond the rx_sensitivity
                dqn_status.reward = -10
                result = self.dqn_trainer.set_observation(dqn_status.current_state, dqn_status.current_action,
                                                          dqn_status.next_state, dqn_status.reward, dqn_status.steps,
                                                          dqn_status.done)
                # start new episode
                if result is True:
                    dqn_status.current_state = (-80, 0)  # initial state is (Rx power, distance)
                    dqn_status.current_action = 0
                    dqn_status.reward = 0
                    dqn_status.next_state = 0
                    dqn_status.done = True
                    dqn_status.steps = 0

    def send_data(self, m_tx_pkt: Packet):
        m_tx_params = BanTxParams()
        m_tx_params.ban_id = self.m_tx_params.ban_id
        m_tx_params.node_id = self.m_tx_params.node_id
        m_tx_params.recipient_id = self.m_tx_params.recipient_id

        self.m_mac.mcps_data_request(self.m_tx_params, m_tx_pkt)

    def get_data(self):
        return self.packet_list

