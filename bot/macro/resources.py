from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from sc2.game_data import Cost

@dataclass
class ResourceData:
    amount: int = 0
    short: bool = False

    def __init__(self, values: Tuple[int, bool]):
        self.amount = values[0]
        self.short = values[1]

    def update(self, cost: int) -> ResourceData:
        if (not self.short and cost <= self.amount):
            return ResourceData((self.amount - cost, False))
        else:
            return ResourceData((self.amount, True))

@dataclass
class Resources:
    minerals: ResourceData
    vespene: ResourceData

    def __init__(self, minerals: ResourceData, vespene: ResourceData) -> None:
        self.minerals = minerals
        self.vespene = vespene

    @classmethod
    def from_tuples(cls, minerals: Tuple[int, bool], vespene: Tuple[int, bool]) -> Resources:
        return cls(ResourceData(minerals), ResourceData(vespene))
    
    @property
    def is_short(self) -> bool:
        return self.minerals.short or self.vespene.short
    
    @property
    def is_short_both(self) -> bool:
        return self.minerals.short and self.vespene.short
    
    def update(self, cost: Cost) -> Tuple[bool, Resources]:
        has_enough_minerals = (
            cost.minerals == 0
            or (self.minerals.amount >= cost.minerals and not self.minerals.short)
        )
        has_enough_vespene = (
            cost.vespene == 0
            or (self.vespene.amount >= cost.vespene and not self.vespene.short)
        )
        can_afford = has_enough_minerals and has_enough_vespene

        if can_afford:
            # If we can afford both, spend the resources normally
            return True, Resources(
                self.minerals.update(cost.minerals),
                self.vespene.update(cost.vespene),
            )
        else:
            # If we can't afford, return the same amounts but correctly mark shortages
            return False, Resources(
                ResourceData((self.minerals.amount, not has_enough_minerals)),
                ResourceData((self.vespene.amount, not has_enough_vespene)),
            )
    
    def debug_print(self) -> None:
        print(f'Resources : {self.minerals.amount} [{self.minerals.short}] / {self.vespene.amount} [{self.vespene.short}]')
