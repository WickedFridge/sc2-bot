import math
from typing import List
from bot.scouting.ghost_units.ghost_units import GhostUnits
from bot.utils.army import Army
from bot.utils.unit_supply import get_units_supply, weighted_units_supply
from sc2.bot_ai import BotAI
from sc2.cache import CachedClass
from sc2.ids.unit_typeid import UnitTypeId
from bot.utils.unit_tags import worker_types, menacing

class GhostArmy(CachedClass):
    ghost_units: GhostUnits

    def __init__(self, ghost_units: GhostUnits, bot: BotAI) -> None:
        super().__init__(bot)
        self.ghost_units = ghost_units
    
    @property
    def tags(self) -> List[int]:
        return self.ghost_units.tags
    
    @property
    def ground_units(self) -> GhostUnits:
        return self.ghost_units.not_flying
    
    @property
    def speed(self) -> float:
        if (self.ghost_units.amount == 0):
            return 0
        self.ghost_units.sort(key = lambda ghost: ghost.real_speed)
        return self.ghost_units.first.real_speed
    
    @property
    def armored_ground_supply(self) -> float:
        armored_ground_ghosts: GhostUnits = self.ground_units.filter(
            lambda ghost: ghost.is_armored
        )
        return get_units_supply(armored_ground_ghosts)
    
    @property
    def armored_ratio(self) -> float:
        if (self.supply == 0):
            return 0
        return self.armored_ground_supply / self.supply
    
    @property
    def flying_fighting_supply(self) -> float:
        return get_units_supply(self.ghost_units.flying.filter(lambda ghost: ghost.can_attack))

    @property
    def supply(self) -> float:
        return get_units_supply(self.ghost_units)

    @property
    def fighting_supply(self) -> int:
        return get_units_supply(self.fighting_units)

    @property
    def weighted_supply(self) -> float:
        return weighted_units_supply(self.fighting_units)
    
    # @property
    # def recap(self) -> dict[str, dict[UnitTypeId, int] | float]:
    #     return {
    #         'units': self.composition,
    #         'supply' : self.supply,
    #     }
    
    # @property
    # def composition(self) -> dict[UnitTypeId, int]:
    #     return Army.get_composition(self.ghost_units)
    
    @property
    def fighting_units(self) -> GhostUnits:
        attacking_units: GhostUnits = self.ghost_units.filter(
            lambda ghost: (
                (ghost.can_attack or ghost.type_id in menacing)
                and ghost.type_id not in worker_types
                and ghost.type_id != UnitTypeId.MEDIVAC
            )
        )
        healing_medivacs: GhostUnits = self.ghost_units(UnitTypeId.MEDIVAC).filter(
            lambda ghost: ghost.energy >= 25
        )
        usable_medivacs: GhostUnits = healing_medivacs.take(attacking_units.amount)
        return attacking_units + usable_medivacs
    
    @property
    def average_ground_range(self) -> float:
        attacking_units: GhostUnits = self.ground_units.filter(lambda ghost: ghost.can_attack)
        if (attacking_units.amount == 0):
            return 0
        total_range: float = sum([ghost.ground_range for ghost in attacking_units])
        return total_range / attacking_units.amount