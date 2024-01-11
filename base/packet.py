from abc import ABC, abstractmethod
from re import T
from ban_seoung_sim.base.antenna_model import AntennaModel
from ban_seoung_sim.wban.wban_header import *
from ban_seoung_sim.wireless_model import *

 
@dataclass
class SpectrumSignalParameters:
    duration: float | None = None
    tx_phy: None = None
    tx_power: float | None = None  # dBm
    tx_antenna: AntennaModel | None = None


class Packet(ABC):
    def __init__(self, packet_size: int):
        self.size: int = packet_size
        self.success: bool = False
        self.spec_tx_params: SpectrumSignalParameters | None = SpectrumSignalParameters()
        self.mac_header: BanMacHeader = BanMacHeader()
        self.mac_frm_body = None

    @abstractmethod
    def set_mac_header(self, *args) -> None:
        pass

    @abstractmethod
    def get_mac_header(self): # -> Mac
        pass

    @abstractmethod
    def set_spectrum_tx_params(self, spec_tx_params: SpectrumSignalParameters):
        self.spec_tx_params = spec_tx_params

    @abstractmethod
    def get_spectrum_tx_params(self) -> SpectrumSignalParameters:
        return self.spec_tx_params

    @abstractmethod
    def get_size(self) -> int:
        pass

    @abstractmethod
    def copy(self): # -> Packet
        pass

    @abstractmethod
    def set_data(self):
        return
