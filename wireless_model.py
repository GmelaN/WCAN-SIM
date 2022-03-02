from tools import *
from mobility_model import *
import random


class PropLossModel:
    def __init__(self):
        self.m_frequency = None
        self.m_lambda = None    # wave length = speed of light in vacuum (m/s) / frequency (Hz)
        self.m_min_loss = 0.0
        self.m_system_loss = 1.0

    def cal_path_loss(self, a: MobilityModel, b: MobilityModel):
        distance = a.get_distance_from(b.get_position())

        distance *= 1000    # convert meter to millimeter

        is_los = a.is_los(b.get_position())

        # We can see the BAN-specific path loss model below
        # G. Dolmans and A. Fort, "Channel models WBAN-holst centre/imec-nl," IEEE 802.15-08-0418-01-0006, 2008.
        a = 15.5
        b = 5.38
        sigma_n = 5.35
        shadowing_db = 9.05    # shadowing factor
        path_loss_db = a * math.log10(distance) + b + sigma_n

        if is_los is False:
            path_loss_db += shadowing_db

        return path_loss_db

    # Calculate the rx power based on friis propagation loss model
    def calc_rx_power_friis(self, tx_power_dbm, a: MobilityModel, b: MobilityModel):
        distance = a.get_distance_from(b.get_position())

        if distance < (3 * self.m_lambda):
            print('distance not within the far field region => inaccurate propagation loss value')
        if distance <= 0:
            return tx_power_dbm - self.m_min_loss

        numerator = self.m_lambda * self.m_lambda
        denominator = 16 * math.pi * math.pi * distance * distance * self.m_system_loss
        loss_db = -10 * math.log10(numerator / denominator)

        return tx_power_dbm - max(loss_db, self.m_min_loss)

    def set_frequency(self, m_frequency):
        self.m_frequency = m_frequency
        # This default value is the propagation speed of light in the vacuum
        c = 299792458  # m/s
        self.m_lambda = c / m_frequency


class PropDelayModel:
    def __init__(self):
        # This default value is the propagation speed of light in the vacuum
        self.m_delay = 299792458  # m/s

    def get_delay(self, a: MobilityModel, b: MobilityModel):
        distance = a.get_distance_from(b.get_position())
        seconds = distance / self.m_delay
        return seconds


class AntennaModel:
    def __init__(self):
        pass

    def get_gain_db(self, angle: Angles):
        pass

