from dataclasses import dataclass
from enum import Enum

from ban_seoung_sim.base.antenna_model import AntennaModel
from ban_seoung_sim.base.mobility_model import MobilityModel
from ban_seoung_sim.base.packet import Packet, SpectrumSignalParameters
from ban_seoung_sim.wban.ban_channel import BanChannel


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
    phy_tx_power: float | None = None
    phy_cca_mode = None
    phy_current_page = None
    phy_max_frame_duration = None
    phy_shr_duration = None
    phy_symbols_per_octet = None

@dataclass
class BanPhyDataAndSymbolRates:
    bit_rate: float | None = None
    symbol_rate: float | None = None

@dataclass
class BanPhyPpduHeaderSymbolNumber:
    shr_preamble: float | None = None
    shr_sfd: float | None = None
    phr: float | None = None


class BanPhy:
    # the turnaround time for for switching the transceiver from RX to TX or vice versa
    aTurnaroundTime = 12

    def __init__(self):
        self.m_env = None
        self.m_rx_sensitivity = None
        self.m_tx_power = None
        self.m_noise = -10   # dB
        self.m_error_model = None
        self.m_channel: BanChannel | None = None
        self.m_mac = None
        self.m_mobility: MobilityModel | None = None
        self.m_antenna: AntennaModel | None = None
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
