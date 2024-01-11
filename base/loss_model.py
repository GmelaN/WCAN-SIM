from abc import ABC, abstractmethod, abstractproperty

from ban_seoung_sim.base.mobility_model import MobilityModel

class LossModel(ABC):
    @abstractmethod
    def cal_path_loss(self, a: MobilityModel, b: MobilityModel):
        pass

    @abstractmethod
    def calc_rx_power_friis(self, tx_power_dbm, a: MobilityModel, b: MobilityModel):
        pass

    @abstractmethod
    def set_frequency(self, m_frequency):
        pass
