from dataclasses import dataclass
from enum import Enum


class BanFrmType(Enum):
    IEEE_802_15_6_MAC_MANAGEMENT = 0
    IEEE_802_15_6_MAC_CONTROL = 1
    IEEE_802_15_6_MAC_DATA = 2


class BanFrmSubType(Enum):
    WBAN_MANAGEMENT_BEACON = 0
    WBAN_CONTROL_IACK = 1
    WBAN_DATA_UP0 = 2
    WBAN_DATA_UP1 = 3
    WBAN_DATA_UP2 = 4
    WBAN_DATA_UP3 = 5
    WBAN_DATA_UP4 = 6
    WBAN_DATA_UP5 = 7
    WBAN_DATA_UP6 = 8
    WBAN_DATA_UP7 = 9
    UNDEFINED = 10


@dataclass
class FrameControl:
    version = None
    ack_policy = None
    sec_level = None
    tk_index = None
    relay = None
    ack_timing = None
    frm_subtype = None
    frm_type = None
    more_data = None
    last_frame = None
    seq_num = None
    frag_num = None
    non_final_frag = None
    reserved = None


@dataclass
class AssignedLinkElement:
    allocation_id: int = None
    interval_start: int = None
    interval_end: int = None
    tx_power: float = None


class BanMacHeader:
    def __init__(self):
        self.frm_control = FrameControl()
        self.ban_id = None
        self.sender_id = None
        self.recipient_id = None

    def set_frm_control(self, frm_type, frm_subtype, ack_policy, seq_num):
        self.frm_control.frm_type = frm_type
        self.frm_control.frm_subtype = frm_subtype
        self.frm_control.ack_policy = ack_policy
        self.frm_control.seq_num = seq_num

    def get_frm_control(self):
        return self.frm_control

    def set_tx_params(self, ban_id, sender_id, recipient_id):
        self.ban_id = ban_id
        self.sender_id = sender_id
        self.recipient_id = recipient_id


class Beacon:
    def __init__(self):
        self.assigned_slot_info = list()  # element type is '@dataclass AssignedLinkElement'

    def set_assigned_link_info(self, assigned_link):
        self.assigned_slot_info.append(assigned_link)

    def get_assigned_link_info(self, n_id):
        for s_info in self.assigned_slot_info:
            if s_info.allocation_id == n_id:
                return s_info
        return None


class IAck:
    def __init__(self):
        pass


class Data:
    def __init__(self, priority):
        self.priority = priority
