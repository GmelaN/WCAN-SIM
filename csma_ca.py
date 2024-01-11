from enum import Enum


class BanMacState(Enum):
    MAC_IDLE = 0
    MAC_CSMA = 1
    MAC_SENDING = 2
    MAC_ACK_PENDING = 3
    CHANNEL_ACCESS_FAILURE = 4
    CHANNEL_IDLE = 5
    SET_PHY_TX_ON = 6


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

