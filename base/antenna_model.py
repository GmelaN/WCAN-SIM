from abc import ABC, abstractmethod
from ban_seoung_sim.base.tools import Angles

class AntennaModel(ABC):    
    @abstractmethod
    def get_gain_db(self, angle: Angles):
        pass
