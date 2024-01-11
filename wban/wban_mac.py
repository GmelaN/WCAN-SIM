from queue import Queue

from ban_seoung_sim.base.packet import Packet
from ban_seoung_sim.base.tracer import Tracer
from ban_seoung_sim.wban.csma_ca import BanMacState, BanPhyTRxState
from ban_seoung_sim.wban.wban_header import BanFrmSubType, BanFrmType
from ban_seoung_sim.wban.wban_packet import WBanPacket
from ban_seoung_sim.wban.wban_phy import BanPhyPibAttributes, BanPibAttributeIdentifier
from ban_seoung_sim.wban.wban_sscs import BanTxOption, BanTxParams


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
        self.m_sscs = None
        self.m_phy = None
        self.m_tx_queue = Queue()          # packet queue
        self.m_tx_pkt: Packet | None = None       # a packet to be sent
        self.m_rx_pkt: Packet | None = None       # a packet received now
        self.m_mac_state = BanMacState.MAC_IDLE
        self.m_mac_rx_on_when_idle = True
        self.m_mac_params = BanTxParams()
        self.trace = Tracer()
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

        ack_pkt = WBanPacket(10)
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
