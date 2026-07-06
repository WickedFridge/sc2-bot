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
        self.ignore_build_order = True
        self.radius = 1
    
    @property
    def expansions_without_turret(self) -> Expansions:
        turrets: Units = self.bot.structures(self.unitId)
        
        return self.bot.expansions.populated.filter(
            lambda expansion: (
                turrets.amount == 0
                or (
                    turrets.closest_distance_to(expansion.turret_mineral_line) > 10
                    and turrets.closest_distance_to(expansion.turret_wall_position) > 10
                )
            )
        )
    
    @property
    @override
    def custom_conditions(self) -> bool:
        enemy_burrow: bool = UpgradeId.BURROW in self.bot.scouting.known_enemy_upgrades
        turrets_not_finished: int = self.bot.structures(self.unitId).not_ready.amount
        
        return (
            enemy_burrow
            and self.expansions_without_turret.amount >= 1
            and (
                self.pending_amount == 0
                or self.pending_amount == turrets_not_finished
            )
        )
    
    @property
    @override
    def position(self) -> Point2:
        return self.expansions_without_turret.first.turret_wall_position