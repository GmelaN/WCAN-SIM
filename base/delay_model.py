from abc import ABC, abstractmethod

from ban_seoung_sim.base.mobility_model import MobilityModel

class DelayModel(ABC):
    @abstractmethod
    def get_delay(self, a: MobilityModel, b: MobilityModel):
        pass    
