from ban_seoung_sim.base.delay_model import DelayModel
from ban_seoung_sim.base.mobility_model import MobilityModel


class PropDelayModel(DelayModel):
    def __init__(self):
        # This default value is the propagation speed of light in the vacuum
        self.m_delay = 299792458  # m/s

    def get_delay(self, a: MobilityModel, b: MobilityModel):
        distance = a.get_distance_from(b.get_position())
        seconds = distance / self.m_delay
        return seconds
