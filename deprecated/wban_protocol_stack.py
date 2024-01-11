from wban_packet import *
from queue import Queue
from wireless_model import *
from mobility_model import *
from tools import *
from trace import *
import math
import numpy as np
from dqn_trainer import NUM_CHANNELS
 

class BanMacState(Enum):
    MAC_IDLE = 0
    MAC_CSMA = 1
    MAC_SENDING = 2
    MAC_ACK_PENDING = 3
    CHANNEL_ACCESS_FAILURE = 4
    CHANNEL_IDLE = 5
    SET_PHY_TX_ON = 6


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


class BanTxOption(Enum):
    TX_OPTION_NONE = 0
    TX_OPTION_ACK = 1
    TX_OPTION_GTS = 2
    TX_OPTION_INDIRECT = 3


class BanPhyTRxState(Enum):
    IEEE_802_15_6_PHY_BUSY = 0
    IEEE_802_15_6_PHY_BUSY_RX = 1
    IEEE_802_15_6_PHY_BUSY_TX = 2
    IEEE_802_15_6_PHY_FORCE_TRX_OFF = 3
    IEEE_802_15_6_PHY_IDLE = 4
    IEEE_802_15_6_PHY_INVALID_PARAMETER = 5
    IEEE_802_15_6_PHY_RX_ON = 6
    IEEE_802_15_6_PHY_SUCCESS = 7
    IEEE_802_15_6_PHY_TRX_OFF = 8
    IEEE_802_15_6_PHY_TX_ON = 9
    IEEE_802_15_6_PHY_UNSUPPORTED_ATTRIBUTE = 10
    IEEE_802_15_6_PHY_READ_ONLY = 11
    IEEE_802_15_6_PHY_UNSPECIFIED = 12


class BanPhyOption(Enum):
    IEEE_802_15_6_868MHZ_BPSK = 0
    IEEE_802_15_6_915MHZ_BPSK = 1
    IEEE_802_15_6_868MHZ_ASK = 2
    IEEE_802_15_6_915MHZ_ASK = 3
    IEEE_802_15_6_868MHZ_OQPSK = 4
    IEEE_802_15_6_915MHZ_OQPSK = 5
    IEEE_802_15_6_2_4GHZ_OQPSK = 6
    IEEE_802_15_6_INVALID_PHY_OPTION = 7


class BanPibAttributeIdentifier(Enum):
    PHY_CURRENT_CHANNEL = 0
    PHY_CHANNELS_SUPPORTED = 1
    PHY_TRANSMIT_POWER = 2
    PHY_CCA_MODE = 3
    PHY_CURRENT_PAGE = 4
    PHY_MAX_FRAME_DURATION = 5
    PHY_SHR_DURATION = 6
    PHY_SYMBOLS_PER_OCTET = 7


@dataclass
class BanPhyPibAttributes:
    phy_current_channel = None
    phy_channels_supported = None
    phy_tx_power: float = None
    phy_cca_mode = None
    phy_current_page = None
    phy_max_frame_duration = None
    phy_shr_duration = None
    phy_symbols_per_octet = None


@dataclass
class BanTxParams:
    ban_id: int = None
    node_id: int = None
    recipient_id: int = None
    seq_num: int = None
    tx_option: BanTxOption = None


@dataclass
class BanPhyDataAndSymbolRates:
    bit_rate: float = None
    symbol_rate: float = None


@dataclass
class BanPhyPpduHeaderSymbolNumber:
    shr_preamble: float = None
    shr_sfd: float = None
    phr: float = None


@dataclass
class DqnStatusInfo:
    node_id = None
    current_state = None
    current_action = None
    reward = None
    next_state = None
    done = None
    steps = None


def seconds(time):
    return time


def milliseconds(time):
    if time == 0:
        return 0.0
    return time / 1000.0


def microseconds(time):
    if time == 0:
        return 0.0
    return time / 1000000.0


# This class can be used to define a new upper layer (APP <-> new upper layer <-> SSCS)
class UpperLayer:
    def __init__(self):
        self.m_env = None
        self.m_sscs = None
        self.m_app = None

    def set_env(self, m_env):
        self.m_env = m_env

    def get_env(self):
        return self.m_env

    def set_app(self, m_app):
        self.m_app = m_app

    def get_app(self):
        return self.m_app

    def set_sscs(self, m_sscs):
        self.m_sscs = m_sscs

    def get_sscs(self):
        return self.m_sscs


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
        self.beacon_interval = milliseconds(255)  # ms
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
                    print('Invalid action')

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
        m_tx_pkt = Packet(10)
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


class BanMac:
    # MAC params specified in IEEE 802.15.6 standard
    pAllocationSlotMin = 500    # us
    pAllocationSlotResolution = 500    # us
    pSIFS = 75  # us
    pMIFS = 20  # us
    pExtraIFS = 10  # us
    mClockResolution = 4  # us
    # A slot length can be calculated as pAllocationSlotMin + (L) * pAllocationSlotResolution = 1000 us (1 ms)
    mAllocationSlotLength = 1  # ms

    def __init__(self):
        self.m_env = None
        self.m_sscs: BanSSCS = None
        self.m_phy: BanPhy = None
        self.m_tx_queue = Queue()          # packet queue
        self.m_tx_pkt: Packet = None       # a packet to be sent
        self.m_rx_pkt: Packet = None       # a packet received now
        self.m_mac_state = BanMacState.MAC_IDLE
        self.m_mac_rx_on_when_idle = True
        self.m_mac_params = BanTxParams()
        self.trace = Trace()
        self.m_csma_ca = None

        self.m_ack_wait_time = None
        self.m_seq_num = None
        self.m_prev_tx_status = False
        self.m_alloc_start_time = None
        self.m_alloc_end_time = None
        self.m_beacon_rx_time = None
        self.m_tx_power = None
        self.initial_energy = None

    def set_env(self, m_env):
        self.m_env = m_env

    def get_env(self):
        return self.m_env

    def set_phy(self, m_phy):
        self.m_phy = m_phy

    def get_phy(self):
        return self.m_phy

    def set_sscs(self, m_sscs):
        self.m_sscs = m_sscs

    def get_sscs(self):
        return self.m_sscs

    def set_csma_ca(self, csma_ca):
        self.m_csma_ca = csma_ca

    def do_initialize(self):
        # TODO: We have to initialize the MAC parameters
        self.m_seq_num = 0
        self.m_alloc_start_time = 0
        self.m_alloc_end_time = 0
        self.m_beacon_rx_time = 0
        self.m_tx_power = 0  # dBm
        self.initial_energy = 1  # watt
        self.trace.set_env(self.m_env)
        self.trace.set_initial_energy(self.initial_energy)

        m_pib_attribute = BanPhyPibAttributes()
        m_pib_attribute.phy_tx_power = self.m_tx_power
        m_pib_attribute.phy_cca_mode = 1
        self.m_phy.set_attribute_request(BanPibAttributeIdentifier.PHY_TRANSMIT_POWER, m_pib_attribute)
        self.m_phy.set_attribute_request(BanPibAttributeIdentifier.PHY_CCA_MODE, m_pib_attribute)

        if self.m_mac_rx_on_when_idle is True:
            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
        else:
            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)

    def set_mac_params(self, m_mac_params):
        self.m_mac_params = m_mac_params

    def mlme_data_request(self, m_tx_pkt: Packet):
        # Push the packet into the Tx queue
        self.m_tx_queue.put_nowait(m_tx_pkt)

        event = self.m_env.event()
        event._ok = True
        event.callbacks.append(self.check_queue)
        self.m_env.schedule(event, priority=0, delay=0)
        # print('\nTime:', round(self.m_env.now, 5), '       Send a beacon frame in the agent (NID:%d)'% self.m_mac_params.node_id)

    def mcps_data_request(self, m_tx_params: BanTxParams, m_tx_pkt: Packet):
        # TODO: Add IEEE 802.15.6 MAC header to the packet
        m_tx_params.tx_option = BanTxOption.TX_OPTION_ACK
        m_tx_params.seq_num = self.m_seq_num
        self.m_seq_num += 1

        m_tx_pkt.set_mac_header(BanFrmType.IEEE_802_15_6_MAC_DATA,
                                BanFrmSubType.WBAN_DATA_UP0, m_tx_params)

        # Push the packet into the Tx queue
        self.m_tx_queue.put_nowait(m_tx_pkt)

        # TODO: To be deleted this code to implement a TDMA
        # self.check_queue()

    # Callback function (called from PHY)
    def pd_data_confirm(self, m_trx_state):
        if m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_SUCCESS:
            # TODO: Check if we have to wait for an ACK
            m_tx_header = self.m_tx_pkt.get_mac_header()

            if (m_tx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_DATA and
                    m_tx_header.get_frm_control().ack_policy == BanTxOption.TX_OPTION_ACK):
                self.set_mac_state(BanMacState.MAC_ACK_PENDING)

                # TODO: Calculate the ack wait time
                self.m_ack_wait_time = (microseconds(self.get_ack_wait_duration() * 1000 * 1000 /
                                                     self.m_phy.get_data_or_symbol_rate(False)))

                self.m_ack_wait_time += (self.m_phy.calc_tx_time(self.m_tx_pkt) * 2)

                event = self.m_env.event()
                event._ok = True
                event.callbacks.append(self.ack_wait_timeout)
                self.m_env.schedule(event, priority=0, delay=self.m_ack_wait_time)
            else:
                self.m_sscs.data_confirm(BanDataConfirmStatus.IEEE_802_15_6_SUCCESS)
                self.m_tx_pkt = None
                self.change_mac_state(BanMacState.MAC_IDLE)
                if self.m_mac_rx_on_when_idle is True:
                    self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
                else:
                    self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)
        elif m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_UNSPECIFIED:
            # TODO: Error report to the upper layer: frame is too long
            pass
        else:
            print('Something went really wrong. The phy is not in the correct state for data transmission')

    # Callback function (called from PHY)
    def pd_data_indication(self, m_rx_pkt: Packet):
        m_rx_header = m_rx_pkt.get_mac_header()

        accept_frame: bool = True

        # TODO: level 1 filtering
        # Check FCS

        # TODO: Level 2 filtering
        # if the sender is me, then discard the received packet
        if m_rx_header.sender_id == self.m_mac_params.node_id:
            accept_frame = False
        if m_rx_header.ban_id != self.m_mac_params.ban_id:
            accept_frame = False
        # broadcast id: 999
        if m_rx_header.recipient_id != 999 and m_rx_header.recipient_id != self.m_mac_params.node_id:
            accept_frame = False

        if accept_frame is True:
            # print('Time:', round(self.m_env.now, 5), '  Received a packet (NID:%d)' % self.m_mac_params.node_id,
            #       'from (NID:%d)' % m_rx_header.sender_id)

            # Beacon received (note: we consider the management-type frame is a beacon frame)
            # Note: broadcast id is 999
            if (m_rx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_MANAGEMENT and
                    m_rx_header.recipient_id == 999):
                self.m_beacon_rx_time = self.m_env.now  # for calculating the remain allocation time

                # TODO: Set the exact start time and end time of the allocation interval
                m_assigned_link = m_rx_pkt.get_frm_body().get_assigned_link_info(self.m_mac_params.node_id)

                if m_assigned_link is not None:
                    # update the new Tx power
                    m_pib_attribute = BanPhyPibAttributes()
                    m_pib_attribute.phy_tx_power = m_assigned_link.tx_power
                    self.m_phy.set_attribute_request(BanPibAttributeIdentifier.PHY_TRANSMIT_POWER, m_pib_attribute)

                    # start time of the allocation interval
                    self.m_alloc_start_time = m_assigned_link.interval_start
                    # number of allocated slots (a slot duration = 1 ms)
                    self.m_alloc_end_time = m_assigned_link.interval_end

                    slot_duration = self.pAllocationSlotMin + self.mAllocationSlotLength*self.pAllocationSlotResolution

                    tx_start_time = microseconds(self.m_alloc_start_time * slot_duration) + microseconds(self.pSIFS)
                    tx_timeout = (microseconds(self.m_alloc_start_time * slot_duration) +
                                  microseconds(self.m_alloc_end_time * slot_duration))

                    self.m_alloc_start_time = tx_start_time
                    self.m_alloc_end_time = tx_timeout

                    event = self.m_env.event()
                    event._ok = True
                    event.callbacks.append(self.start_tx)
                    self.m_env.schedule(event, priority=0, delay=self.m_alloc_start_time)

            # for further processing the received control or data-type frame
            self.m_rx_pkt = m_rx_pkt

            # data frame received
            if m_rx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_DATA:
                # if it is a data frame, push it up the stack
                self.m_sscs.data_indication(self.m_rx_pkt)

                # if this is a data or management-type frame, which is not a broadcast,
                # generate and send an ACK frame.
                # if the MAC state is MAC_ACK_PENDING, then we drop the packet that just sent before (data packet)
                if (self.m_mac_state == BanMacState.MAC_ACK_PENDING and
                        m_rx_header.get_frm_control().ack_policy == BanTxOption.TX_OPTION_ACK):
                    # TODO: Prepare retransmission

                    self.m_tx_pkt = None
                    self.set_mac_state(BanMacState.MAC_IDLE)
                    self.m_sscs.data_confirm(BanDataConfirmStatus.IEEE_802_15_6_NO_ACK)

                # cancel any pending MAC state change ACKs have higher priority
                if m_rx_header.get_frm_control().ack_policy == BanTxOption.TX_OPTION_ACK:
                    self.change_mac_state(BanMacState.MAC_IDLE)
                    event = self.m_env.event()
                    event._ok = True
                    event.callbacks.append(self.send_ack)
                    self.m_env.schedule(event, priority=0, delay=(self.pSIFS * 0.000001))

            # control-type frame (ACK) received
            elif (m_rx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_CONTROL and
                  self.m_tx_pkt is not None and self.m_mac_state.MAC_ACK_PENDING):
                # if it is an ACK with the expected sequence number,
                # finish the transmission and notify the upper layer
                m_tx_header = self.m_tx_pkt.get_mac_header()

                if m_rx_header.get_frm_control().seq_num == m_tx_header.get_frm_control().seq_num:
                    # if the packet that just sent before is a data frame
                    if m_tx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_DATA:
                        # update trace info
                        self.trace.add_success_tx_pkt(self.m_tx_pkt)

                        self.m_sscs.data_confirm(BanDataConfirmStatus.IEEE_802_15_6_SUCCESS)

                        # Prepare the next transmission
                        self.m_tx_pkt = None
                        self.m_prev_tx_status = True    # mark the current Tx result as a success
                        self.change_mac_state(BanMacState.MAC_IDLE)
                        if self.m_mac_rx_on_when_idle is True:
                            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
                        else:
                            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)
                        event = self.m_env.event()
                        event._ok = True
                        event.callbacks.append(self.check_queue)
                        self.m_env.schedule(event, priority=0, delay=self.pSIFS * 0.000001)
                    else:
                        # Do nothing
                        pass
                else:
                    # TODO: prepare retransmission
                    self.m_prev_tx_status = False   # mark the current Tx result as a fail
                    self.m_sscs.data_confirm(BanDataConfirmStatus.IEEE_802_15_6_COUNTER_ERROR)

    # Callback function (called from PHY)
    def set_trx_state_confirm(self, status: BanPhyTRxState):
        if self.m_mac_state == BanMacState.MAC_SENDING and status == BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON:
            if self.m_tx_pkt is None:
                print('Fatal error: No Tx packet')
                return

            # TODO: We give up the current transmission according to the three conditions below
            # Cond 1) if the current time is not in the boundary of allocation intervals
            # Cond 2) if the expected Tx time is over the remain allocation intervals
            # Cond 3) if the remain allocation interval is lower than the minimum time slot unit

            slot_duration = self.pAllocationSlotMin + self.mAllocationSlotLength * self.pAllocationSlotResolution
            guard_time = microseconds(self.pSIFS + self.pExtraIFS + self.mClockResolution)
            expected_tx_time = self.m_phy.calc_tx_time(self.m_tx_pkt)
            remain_alloc_time = ((self.m_alloc_end_time - self.m_alloc_start_time) -
                                 (self.m_env.now - self.m_beacon_rx_time - self.m_alloc_start_time))

            # TODO: We have to re-calculate the expected ack_rx_time instead of the constant value (expected_tx_time)
            ack_rx_time = self.m_phy.calc_tx_time(self.m_tx_pkt)

            m_tx_header = self.m_tx_pkt.get_mac_header()

            if m_tx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_CONTROL:
                # Do nothing
                pass
            elif m_tx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_MANAGEMENT:
                # Do nothing
                pass
            elif m_tx_header.get_frm_control().frm_type == BanFrmType.IEEE_802_15_6_MAC_DATA:
                if (microseconds(slot_duration) >= remain_alloc_time or
                        (expected_tx_time + guard_time + ack_rx_time) >= remain_alloc_time):
                    self.change_mac_state(BanMacState.MAC_IDLE)
                    if self.m_mac_rx_on_when_idle is True:
                        self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
                    else:
                        self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)

                    # print('Expected Tx time:', expected_tx_time, 'Remain alloc time:', remain_alloc_time)
                    return

            self.m_phy.pd_data_request(self.m_tx_pkt)

        elif self.m_mac_state == BanMacState.MAC_CSMA and (status == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON
                                                           or status == BanPhyTRxState.IEEE_802_15_6_PHY_SUCCESS):
            # Start the CSMA algorithm as soon as the receiver is enabled
            self.m_csma_ca.start()

        elif self.m_mac_state == BanMacState.MAC_IDLE:
            # print('Do nothing special when going idle')
            pass
        elif self.m_mac_state == BanMacState.MAC_ACK_PENDING:
            # print('Do nothing special when waiting an ACK')
            pass
        else:
            print('Error changing transceiver state')

    def start_tx(self, event):
        if self.m_tx_pkt is not None:
            if self.m_mac_state == BanMacState.MAC_IDLE:
                self.change_mac_state(BanMacState.MAC_SENDING)
                self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)
            elif self.m_mac_state == BanMacState.MAC_ACK_PENDING:
                self.set_mac_state(BanMacState.MAC_IDLE)
        else:
            self.set_mac_state(BanMacState.MAC_IDLE)

    def check_queue(self, event):
        if self.m_mac_state == BanMacState.MAC_IDLE and self.m_tx_queue.empty() is False and self.m_tx_pkt is None:
            self.m_tx_pkt = self.m_tx_queue.get_nowait()
            self.change_mac_state(BanMacState.MAC_SENDING)
            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)

    def change_mac_state(self, new_state: BanMacState):
        self.m_mac_state = new_state

    def set_mac_state(self, mac_state: BanMacState):
        if mac_state == BanMacState.MAC_IDLE:
            self.change_mac_state(BanMacState.MAC_IDLE)
            if self.m_mac_rx_on_when_idle is True:
                self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
            else:
                self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)
            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.check_queue)
            self.m_env.schedule(event, priority=0, delay=0)

        elif mac_state == BanMacState.MAC_ACK_PENDING:
            self.change_mac_state(BanMacState.MAC_ACK_PENDING)
            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)

        # CSMA/CA conditions
        elif mac_state == BanMacState.MAC_CSMA:
            if self.m_mac_state != BanMacState.MAC_IDLE or self.m_mac_state != BanMacState.MAC_ACK_PENDING:
                print('Fatal error: CSMA/CA')
            self.change_mac_state(BanMacState.MAC_CSMA)
            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)

        elif self.m_mac_state == BanMacState.MAC_CSMA and mac_state == BanMacState.CHANNEL_IDLE:
            self.change_mac_state(BanMacState.MAC_SENDING)
            self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)

        elif self.m_mac_state == BanMacState.MAC_CSMA and mac_state == BanMacState.CHANNEL_ACCESS_FAILURE:
            print('Cannot find clear channel, drop the tx pkt')
            self.m_tx_pkt = None
            self.change_mac_state(BanMacState.MAC_IDLE)

    def send_ack(self, event):
        if self.m_mac_state != BanMacState.MAC_IDLE:
            print('Invalid MAC state')

        ack_pkt = Packet(10)
        m_tx_params = BanTxParams()
        m_tx_params.ban_id = self.m_mac_params.ban_id
        m_tx_params.node_id = self.m_mac_params.node_id
        m_tx_params.recipient_id = self.m_rx_pkt.get_mac_header().sender_id
        m_tx_params.tx_option = BanTxOption.TX_OPTION_NONE
        m_tx_params.seq_num = self.m_rx_pkt.get_mac_header().get_frm_control().seq_num

        ack_pkt.set_mac_header(BanFrmType.IEEE_802_15_6_MAC_CONTROL, BanFrmSubType.WBAN_CONTROL_IACK, m_tx_params)

        # Enqueue the ACK packet for further processing when the transceiver is activated
        self.m_tx_pkt = ack_pkt

        # Switch transceiver to Tx mode. Proceed sending the Ack on confirm
        self.change_mac_state(BanMacState.MAC_SENDING)
        self.m_phy.set_trx_state_request(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)

    def ack_wait_timeout(self, event):
        # Check whether this timeout is called for previous tx packet or called for current tx packet
        if self.m_prev_tx_status is True:
            self.m_prev_tx_status = False   # this flag will be turned on when the node receives a corresponding Ack
            return

        if self.m_mac_state == BanMacState.MAC_ACK_PENDING:
            # Simply drop the pending packet
            self.m_tx_pkt = None
            self.set_mac_state(BanMacState.MAC_IDLE)
            self.m_sscs.data_confirm(BanDataConfirmStatus.IEEE_802_15_6_NO_ACK)
        else:
            # Do nothing
            pass

    def get_ack_wait_duration(self):
        # TODO: Calculate the ack wait duration
        return (self.m_phy.aTurnaroundTime + self.m_phy.get_phy_shr_duration() +
                (math.ceil(6 * self.m_phy.get_phy_symbols_per_octet())))

    def set_attribute_confirm(self, status, attribute_id):
        # print('set_attribute_confirm:', status, attribute_id)
        pass

    def plme_cca_confirm(self, status: BanPhyTRxState):
        self.m_csma_ca.plme_cca_confirm(status)

    def show_result(self, event):
        print('Performance results (NID: %d)' % self.m_mac_params.node_id)
        print('Packet delivery ratio:', round(self.trace.get_pkt_delivery_ratio(), 2) * 100, '%')
        print('Throughput:', round(self.trace.get_throughput() / 1000, 3), 'kbps')
        print('Energy consumption ratio:', round(self.trace.get_energy_consumption_ratio(), 3), '%', '\n')

        self.trace.reset()
        event = self.m_env.event()
        event._ok = True
        event.callbacks.append(self.show_result)
        self.m_env.schedule(event, priority=0, delay=200)


class BanPhy:
    # the turnaround time for for switching the transceiver from RX to TX or vice versa
    aTurnaroundTime = 12

    def __init__(self):
        self.m_env = None
        self.m_rx_sensitivity = None
        self.m_tx_power = None
        self.m_noise = -10   # dB
        self.m_error_model = None
        self.m_channel: BanChannel = None
        self.m_mac: BanMac = None
        self.m_mobility: MobilityModel = None
        self.m_antenna: AntennaModel = None
        self.m_cca_peak_power = 0.0

        self.m_pib_attributes = BanPhyPibAttributes()
        self.m_rx_pkt = None
        self.m_phy_option = BanPhyOption.IEEE_802_15_6_INVALID_PHY_OPTION
        self.m_data_symbol_rates: BanPhyDataAndSymbolRates = ((20.0, 20.0),
                                                              (40.0, 40.0),
                                                              (250.0, 12.5),
                                                              (250.0, 50.0),
                                                              (100.0, 25.0),
                                                              (250.0, 62.5),
                                                              (250.0, 62.5))
        self.m_ppdu_header_symbol_num: BanPhyPpduHeaderSymbolNumber = ((32.0, 8.0, 8.0),
                                                                       (32.0, 8.0, 8.0),
                                                                       (2.0, 1.0, 0.4),
                                                                       (6.0, 1.0, 1.6),
                                                                       (8.0, 2.0, 2.0),
                                                                       (8.0, 2.0, 2.0),
                                                                       (8.0, 2.0, 2.0))

        self.m_trx_state = BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF

    def set_env(self, m_env):
        self.m_env = m_env

    def get_env(self):
        return self.m_env

    # For calling the MAC functions (callback)
    def set_mac(self, m_mac):
        self.m_mac = m_mac

    def get_mac(self):
        return self.m_mac

    def set_channel(self, m_channel):
        self.m_channel = m_channel
        self.m_channel.add_phy_list(self)

    def get_channel(self):
        return self.m_channel

    def set_mobility(self, m_mobility):
        self.m_mobility = m_mobility

    def get_mobility(self):
        return self.m_mobility

    def set_rx_pkt(self, m_rx_pkt):
        self.m_rx_pkt = m_rx_pkt

    def set_antenna(self, antenna):
        self.m_antenna = antenna

    def get_rx_antenna(self):
        return self.m_antenna

    def do_initialize(self):
        self.m_phy_option = BanPhyOption.IEEE_802_15_6_915MHZ_OQPSK
        self.m_rx_sensitivity = -82  # dBm

    def set_attribute_request(self, attribute_id: BanPibAttributeIdentifier, attribute: BanPhyPibAttributes):
        status = BanPhyTRxState.IEEE_802_15_6_PHY_SUCCESS

        # TODO: Support the other options layer (except for setting up the transmit power)
        if attribute_id == BanPibAttributeIdentifier.PHY_TRANSMIT_POWER:
            if attribute.phy_tx_power > 0xbf:
                status = BanPhyTRxState.IEEE_802_15_6_PHY_INVALID_PARAMETER
            else:
                self.m_pib_attributes.phy_tx_power = attribute.phy_tx_power

        elif attribute_id == BanPibAttributeIdentifier.PHY_CURRENT_CHANNEL:
            status = BanPhyTRxState.IEEE_802_15_6_PHY_UNSUPPORTED_ATTRIBUTE
        elif attribute_id == BanPibAttributeIdentifier.PHY_CHANNELS_SUPPORTED:
            status = BanPhyTRxState.IEEE_802_15_6_PHY_UNSUPPORTED_ATTRIBUTE
        elif attribute_id == BanPibAttributeIdentifier.PHY_CCA_MODE:
            if attribute.phy_cca_mode < 1 or attribute.phy_cca_mode > 3:
                status = BanPhyTRxState.IEEE_802_15_6_PHY_INVALID_PARAMETER
            else:
                self.m_pib_attributes.phy_cca_mode = attribute.phy_cca_mode
        else:
            status = BanPhyTRxState.IEEE_802_15_6_PHY_UNSUPPORTED_ATTRIBUTE

        self.m_mac.set_attribute_confirm(status, attribute_id)

    def get_data_or_symbol_rate(self, is_data: bool):
        rate = 0.0
        if self.m_phy_option == BanPhyOption.IEEE_802_15_6_INVALID_PHY_OPTION:
            print('Invalid phy option (modulation)')
            return
        if is_data is True:
            rate = self.m_data_symbol_rates[self.m_phy_option.value][0]  # data rate
        else:
            rate = self.m_data_symbol_rates[self.m_phy_option.value][1]  # symbol rate
        return rate * 1000.0

    def set_trx_state_request(self, new_state):
        # TODO: callback the function (set_trx_state_confirm()) in the BanMac class
        # Trying to set m_trx_state to new_state

        if self.m_trx_state == new_state:
            self.m_mac.set_trx_state_confirm(new_state)
            return

        if ((new_state == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON or
             new_state == BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF) and
                self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_TX):
            # TODO: Phy is busy; setting state pending to
            # return  # Send set_trx_state_confirm() later
            self.change_trx_state(new_state)
            self.m_mac.set_trx_state_confirm(new_state)

        if new_state == BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF:
            # TODO: Cancel Energy Detection (ED)

            if self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX:
                # TODO: Phy is busy; setting state pending to
                # return  # Send set_trx_state_confirm() later
                self.change_trx_state(new_state)
                self.m_mac.set_trx_state_confirm(new_state)
            elif (self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON or
                  self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON):
                self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)
                self.m_mac.set_trx_state_confirm(new_state)
                return

        # turn on PHY_TX_ON
        if new_state == BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON:
            # terminate reception if needed
            # incomplete reception -- force packet discard
            # TODO: Mark the TRX state as a Pending state until the current reception ends
            # TODO: After the current reception ends, we set the TRX state to PHY_TX_ON
            if (self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX or
                    self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON):
                self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)
                self.m_mac.set_trx_state_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)
                return
            # We do not change the transceiver state here.
            # We only report that the transceiver is already in Tx_On state
            elif (self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_TX or
                  self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON):
                self.m_mac.set_trx_state_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)
                return
            # Simply set the transceiver to Tx mode
            elif self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF:
                self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)
                self.m_mac.set_trx_state_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON)
                return

        if new_state == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON:
            if (self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON or
                    self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF):
                # TODO: Mark the TRX state as a Pending state until the current transmission ends
                # TODO: After the current transmission ends, we set the TRX state to PHY_RX_ON
                self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
                self.m_mac.set_trx_state_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
                return
            # Simply set the transceiver to Rx mode
            if self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX:
                self.m_mac.set_trx_state_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)
                return

    def change_trx_state(self, new_state):
        self.m_trx_state = new_state

    def pd_data_request(self, m_tx_pkt: Packet):
        if self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TX_ON:
            # TODO: after the Tx duration expires, we call the function (end_tx()) to complete the current transmission
            self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_TX)

            # TODO: set the Tx duration, tx_phy, tx_antenna
            spec_tx_params = SpectrumSignalParameters()
            tx_duration = self.calc_tx_time(m_tx_pkt)
            spec_tx_params.duration = tx_duration
            spec_tx_params.tx_phy = self
            spec_tx_params.tx_power = self.m_pib_attributes.phy_tx_power
            spec_tx_params.tx_antenna = self.m_antenna

            # Add the spectrum Tx parameters to the Tx_pkt
            m_tx_pkt.set_spectrum_tx_params(spec_tx_params)

            # We have to previously forward the required parameter before we register the event of a function call
            self.m_channel.set_tx_pkt(m_tx_pkt)

            # update trace info
            self.m_mac.trace.add_tx_pkt(m_tx_pkt)

            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.m_channel.start_tx)
            event.callbacks.append(self.end_tx)
            self.m_env.schedule(event, priority=0, delay=tx_duration)

        # Transmission fails because the transceiver is not prepared to send a packet
        elif (self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON or
              self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF or
              self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_TX):

            self.m_mac.pd_data_confirm(self.m_trx_state)

    def end_tx(self, event):
        # If the transmission successes
        self.m_mac.pd_data_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_SUCCESS)

        # If the transmission aborted
        # self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)

        # print('Time:', round(self.m_env.now, 5), '  Send a packet at the physical layer (NID:%d)'
        #       % self.m_mac.m_mac_params.node_id)

        # if the transmission fails

    def start_rx(self, event):
        if self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON:
            # TODO: Calculate interference, noise, and SINR
            # If the 10*log10 (sinr) > -5, then receive the packet, otherwise drop the packet
            self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX)

            if self.m_rx_pkt.get_spectrum_tx_params().tx_power + self.m_noise >= self.m_rx_sensitivity:
                self.m_rx_pkt.success = True
            else:
                self.m_rx_pkt.success = False
            # print('Rx power (dBm):', self.m_rx_pkt.get_spectrum_tx_params().tx_power + self.m_noise)
        elif self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX:
            # TODO: Drop the packet
            print('Packet collision at (NID:%d)' % self.m_mac.m_mac_params.node_id, self.m_trx_state)
            self.m_rx_pkt.success = False
        else:
            # TODO: Drop the packet
            print('Transceiver not in Rx state:', self.m_trx_state)
            self.m_rx_pkt.success = False

        # Update peak power if CCA is in progress
        power = self.m_rx_pkt.get_spectrum_tx_params().tx_power + self.m_noise
        if self.m_cca_peak_power < power:
            self.m_cca_peak_power = power

        # TODO: after the Rx duration expires, we call the function (end_rx()) to complete the current reception
        rx_duration = self.calc_tx_time(self.m_rx_pkt)

        event = self.m_env.event()
        event._ok = True
        event.callbacks.append(self.end_rx)
        self.m_env.schedule(event, priority=0, delay=rx_duration)

    def end_rx(self, event):
        # TODO: Update the average receive power during ED
        # TODO: Check interference
        # TODO: Check if reception was successful
        # TODO: Update LQI using error model

        # If the packet was successfully received, push it up the stack
        if self.m_rx_pkt.success is True:
            self.m_mac.pd_data_indication(self.m_rx_pkt)

        if self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX:
            self.change_trx_state(BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON)

    def calc_tx_time(self, m_tx_pkt):
        is_data = True
        # TODO: Calculate header tx time
        tx_time = self.get_ppdu_header_tx_time()

        tx_time += (m_tx_pkt.get_size() * 8.0 / self.get_data_or_symbol_rate(is_data))  # seconds
        return tx_time

    def get_ppdu_header_tx_time(self):
        is_data = False
        if self.m_phy_option != BanPhyOption.IEEE_802_15_6_INVALID_PHY_OPTION:
            total_ppdu_hdr_symbols = (self.m_ppdu_header_symbol_num[self.m_phy_option.value][0] +
                                      self.m_ppdu_header_symbol_num[self.m_phy_option.value][1] +
                                      self.m_ppdu_header_symbol_num[self.m_phy_option.value][2])
        else:
            print('fatal error: Invalid phy option')
            return None
        return seconds((total_ppdu_hdr_symbols / self.get_data_or_symbol_rate(is_data)))

    def get_phy_shr_duration(self):
        if self.m_phy_option != BanPhyOption.IEEE_802_15_6_INVALID_PHY_OPTION:
            return (self.m_ppdu_header_symbol_num[self.m_phy_option.value][0] +
                    self.m_ppdu_header_symbol_num[self.m_phy_option.value][1])
        else:
            print('fatal error: Invalid phy option')
            return None

    def get_phy_symbols_per_octet(self):
        if self.m_phy_option != BanPhyOption.IEEE_802_15_6_INVALID_PHY_OPTION:
            return (self.m_data_symbol_rates[self.m_phy_option.value][1] /
                    (self.m_data_symbol_rates[self.m_phy_option.value][0] / 8))
        else:
            print('fatal error: Invalid phy option')
            return None

    def plme_cca_request(self):
        if (self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_RX_ON or
                self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX):
            self.m_cca_peak_power = 0.0
            cca_time = seconds(8.0 / self.get_data_or_symbol_rate(False))

            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.end_cca)
            self.m_env.schedule(event, priority=0, delay=cca_time)  # clear channel assessment during cca_time
        else:
            if self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF:
                self.m_mac.plme_cca_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_TRX_OFF)
            else:
                self.m_mac.plme_cca_confirm(BanPhyTRxState.IEEE_802_15_6_PHY_BUSY)

    def end_cca(self, event):
        sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_UNSPECIFIED

        # From here, we evaluate the historical channel state during cca_time
        if self.phy_is_busy() is True:
            sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_BUSY
        elif self.m_pib_attributes.phy_cca_mode == 1:
            if 10 * math.log10(self.m_cca_peak_power / self.m_rx_sensitivity) >= 10.0:
                sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_BUSY
                print('CCA result =', sensed_channel_state)
            else:
                sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_IDLE
                print('CCA result =', sensed_channel_state)
        elif self.m_pib_attributes.phy_cca_mode == 2:
            if self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX:
                sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_BUSY
            else:
                sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_IDLE
        elif self.m_pib_attributes.phy_cca_mode == 3:
            if (10 * math.log10(self.m_cca_peak_power / self.m_rx_sensitivity) >= 10.0 and
                    self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX):
                sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_BUSY
            else:
                sensed_channel_state = BanPhyTRxState.IEEE_802_15_6_PHY_IDLE
        else:
            print('fatal error: Invalid CCA mode')

        self.m_mac.plme_cca_confirm(sensed_channel_state)

    def phy_is_busy(self):
        return (self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_TX or
                self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY_RX or
                self.m_trx_state == BanPhyTRxState.IEEE_802_15_6_PHY_BUSY)


class BanChannel:
    def __init__(self, env):
        self.m_env = env
        self.prop_loss_model = PropLossModel()       # propagation loss model
        self.prop_delay_model = PropDelayModel()     # delay model
        self.path_loss_model = None                  # path loss model

        self.max_loss_db = 1.0e9
        self.m_tx_pkt = None
        self.m_phy_list = list()     # send a data packet to all the registered phy modules

    def add_phy_list(self, m_phy):
        self.m_phy_list.append(m_phy)

    def set_prop_loss_model(self, prop_loss_model):
        self.prop_loss_model = prop_loss_model

    def set_prop_delay_model(self, prop_delay_model):
        self.prop_delay_model = prop_delay_model

    def set_tx_pkt(self, m_tx_pkt):
        self.m_tx_pkt = m_tx_pkt

    def start_tx(self, event):
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


class CsmaCa:
    def __init__(self):
        self.m_env = None
        self.m_mac = None
        self.m_is_slotted = False   # beacon-enabled slotted or nonbeacon-enabled unslotted CSMA/CA
        self.m_nb = 0   # number of backoffs for the current transmission
        self.m_cw = 2   # contention window length (used in slotted ver only)
        self.m_be = 3   # backoff exponent
        self.m_ble = False  # battery life extension
        self.m_mac_min_backoff_exp = 3   # minimum backoff exponent
        self.m_mac_max_backoff_exp = 5   # maximum backoff exponent
        self.m_mac_max_csma_backoffs = 4    # maximum number of backoffs
        self.m_unit_backoff_period = 20   # number of symbols per CSMA/CA time unit, default 20 symbols
        self.m_cca_request_running = False  # flag indicating that the PHY is currently running a CCA

    def set_env(self, m_env):
        self.m_env = m_env

    def get_env(self):
        return self.m_env

    def set_mac(self, m_mac):
        self.m_mac = m_mac

    def get_mac(self):
        return self.m_mac

    def set_slotted_csma_ca(self):
        self.m_is_slotted = True

    def set_unslotted_csma_ca(self):
        self.m_is_slotted = False

    def is_slotted_csma_ca(self):
        return self.m_is_slotted

    def is_unslotted_csma_ca(self):
        return not self.m_is_slotted

    def set_mac_min_backoff_exp(self, min_backoff_exp):
        self.m_mac_min_backoff_exp = min_backoff_exp

    def get_mac_min_backoff_exp(self):
        return self.m_mac_min_backoff_exp

    def set_mac_max_backoff_exp(self, max_backoff_exp):
        self.m_mac_max_backoff_exp = max_backoff_exp

    def get_mac_max_backoff_exp(self):
        return self.m_mac_max_backoff_exp

    def set_mac_max_csma_backoffs(self, max_csma_backoffs):
        self.m_mac_max_csma_backoffs = max_csma_backoffs

    def get_mac_max_csma_backoffs(self):
        return self.m_mac_max_csma_backoffs

    def set_unit_backoff_period(self, unit_backoff_period):
        self.m_unit_backoff_period = unit_backoff_period

    def get_unit_backoff_period(self):
        return self.m_unit_backoff_period

    def get_time_to_next_slot(self):
        # TODO: calculate the offset to the next slot
        return 0

    def start(self):
        self.m_nb = 0
        if self.is_slotted_csma_ca() is True:
            self.m_cw = 2;
            if self.m_ble is True:
                self.m_be = min(2, self.m_mac_min_backoff_exp)
            else:
                self.m_be = self.m_mac_min_backoff_exp
            # TODO: for slotted, locate backoff period boundary, i.e., delay to the next slot boundary
            backoff_boundary = self.get_time_to_next_slot()

            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.random_backoff_delay)
            self.m_env.schedule(event, priority=0, delay=backoff_boundary)
        else:
            self.m_be = self.m_mac_min_backoff_exp

            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.random_backoff_delay)
            self.m_env.schedule(event, priority=0, delay=0)

    def cancel(self):
        pass

    def random_backoff_delay(self, event):
        upper_bound = pow(2, self.m_be -1)
        is_data = False

        symbol_rate = self.m_mac.get_phy().get_data_or_symbol_rate(is_data)    # symbols per second
        backoff_period = random.uniform(0, upper_bound + 1)    # number of backoff periods
        random_backoff = microseconds(backoff_period * self.get_unit_backoff_period() * 1000 * 1000 / symbol_rate)

        if self.is_unslotted_csma_ca() is True:
            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.request_cca)
            self.m_env.schedule(event, priority=0, delay=random_backoff)
        else:
            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.can_proceed)
            self.m_env.schedule(event, priority=0, delay=random_backoff)

    def can_proceed(self, event):
        can_proceed = True

        if can_proceed is True:
            # TODO: for slotted, perform CCA on backoff period boundary, i.e., delay to next slot boundary
            backoff_boundary = self.get_time_to_next_slot()

            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.request_cca)
            self.m_env.schedule(event, priority=0, delay=backoff_boundary)
        else:
            next_cap = 0

            event = self.m_env.event()
            event._ok = True
            event.callbacks.append(self.random_backoff_delay)
            self.m_env.schedule(event, priority=0, delay=next_cap)

    def request_cca(self, event):
        self.m_cca_request_running = True
        self.m_mac.get_phy().plme_cca_request()

    def plme_cca_confirm(self, status: BanPhyTRxState):
        if self.m_cca_request_running is True:
            self.m_cca_request_running = False

            if status == BanPhyTRxState.IEEE_802_15_6_PHY_IDLE:
                if self.is_slotted_csma_ca() is True:
                    self.m_cw -= 1
                    if self.m_cw == 0:
                        self.m_mac.set_mac_state(BanMacState.CHANNEL_IDLE)
                    else:
                        event = self.m_env.event()
                        event._ok = True
                        event.callbacks.append(self.request_cca)
                        self.m_env.schedule(event, priority=0, delay=0)
                else:
                    self.m_mac.set_mac_state(BanMacState.CHANNEL_IDLE)
            else:
                if self.is_slotted_csma_ca() is True:
                    self.m_cw = 2
                self.m_be = min(self.m_be + 1, self.m_mac_max_backoff_exp)
                self.m_nb += 1
                if self.m_nb > self.m_mac_max_csma_backoffs:
                    # no channel found so cannot send packet
                    self.m_mac.set_mac_state(BanMacState.CHANNEL_ACCESS_FAILURE)
                    return
                else:
                    # perform another backoff (step 2)
                    event = self.m_env.event()
                    event._ok = True
                    event.callbacks.append(self.random_backoff_delay)
                    self.m_env.schedule(event, priority=0, delay=0)

    def get_nb(self):
        # return the number of CSMA retries
        return self.m_nb

