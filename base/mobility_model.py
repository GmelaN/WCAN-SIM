from abc import ABC, abstractmethod
from ban_seoung_sim.base.tools import Vector


class MobilityModel(ABC):
    @abstractmethod
    def get_position(self) -> Vector:
        pass

    @abstractmethod
    def set_position(self, position: Vector):
        pass

    @abstractmethod
    def get_body_position(self) -> Vector:
        pass

    @abstractmethod
    def get_distance_from(self, position: Vector) -> float:
        pass

    @abstractmethod
    def is_los(self, position: Vector):
        pass
