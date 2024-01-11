from ban_seoung_sim.base.packet import Packet, SpectrumSignalParameters
from ban_seoung_sim.wban.wban_header import *
from ban_seoung_sim.wireless_model import *


class WBanPacket(Packet):
    def __init__(self, pkt_size):
        self.size = pkt_size
        self.success = False
        self.spec_tx_params = SpectrumSignalParameters()

        self.mac_header = BanMacHeader()
        self.mac_frm_body = None

    def set_mac_header(self, frm_type, frm_subtype, m_tx_params):
        self.mac_header.set_tx_params(m_tx_params.ban_id, m_tx_params.node_id, m_tx_params.recipient_id)
        self.mac_header.set_frm_control(frm_type, frm_subtype, m_tx_params.tx_option, m_tx_params.seq_num)

        if frm_subtype == BanFrmSubType.WBAN_MANAGEMENT_BEACON:
            self.mac_frm_body = Beacon()
        elif frm_subtype == BanFrmSubType.WBAN_CONTROL_IACK:
            self.mac_frm_body = IAck()
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP0:
            self.mac_frm_body = Data(0)
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP1:
            self.mac_frm_body = Data(1)
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP2:
            self.mac_frm_body = Data(2)
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP3:
            self.mac_frm_body = Data(3)
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP4:
            self.mac_frm_body = Data(4)
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP5:
            self.mac_frm_body = Data(5)
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP6:
            self.mac_frm_body = Data(6)
        elif frm_subtype == BanFrmSubType.WBAN_DATA_UP7:
            self.mac_frm_body = Data(7)
        else:
            self.mac_frm_body = None
            print('frame initialization error (invalid frame subtype)')

    def get_mac_header(self):
        return self.mac_header

    def get_frm_body(self):
        return self.mac_frm_body

    def set_spectrum_tx_params(self, spec_tx_params: SpectrumSignalParameters):
        self.spec_tx_params = spec_tx_params

    def get_spectrum_tx_params(self):
        return self.spec_tx_params

    def get_size(self):
        return self.size

    def copy(self):
        new_packet = WBanPacket(self.size)
        new_packet.success = self.success
        new_packet.spec_tx_params = self.spec_tx_params
        new_packet.mac_header = self.mac_header
        new_packet.mac_frm_body = self.mac_frm_body

        return new_packet

    def set_data(self):
        return
