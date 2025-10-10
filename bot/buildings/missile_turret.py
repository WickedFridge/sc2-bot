from typing import override
from bot.buildings.building import Building
from bot.macro.expansion_manager import Expansions
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.units import Units


class MissileTurret(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.MISSILETURRET
        self.name = "Missile Turret"

    
    @property
    def expansions_without_turret(self) -> Expansions:
        return self.bot.expansions.populated.filter(
            lambda expansion: (
                self.bot.structures(UnitTypeId.MISSILETURRET).amount == 0 
                or self.bot.structures(UnitTypeId.MISSILETURRET).closest_distance_to(expansion.position) > 12
            )
        )
    
    @override
    @property
    def conditions(self) -> bool:
        have_ebay: bool = self.bot.structures(UnitTypeId.ENGINEERINGBAY).ready.amount >= 1
        enemy_burrow: bool = UpgradeId.BURROW in self.bot.scouting.known_enemy_upgrades
        turret_to_construct_amount: int = self.bot.already_pending(UnitTypeId.MISSILETURRET) - self.bot.structures(UnitTypeId.MISSILETURRET).not_ready.amount
        
        return (
            have_ebay
            and enemy_burrow
            and self.expansions_without_turret.amount >= 1
            and turret_to_construct_amount == 0
        )
    
    @override
    @property
    def position(self) -> Point2:
        return self.expansions_without_turret.first.bunker_forward_in_pathing