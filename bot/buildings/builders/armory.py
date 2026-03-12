from typing import override
from bot.army_composition.composition import Composition
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class Armory(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.ARMORY
        self.name = "Armory"

    # @override
    # @property
    # def override_conditions(self):
    #     return self.amount == 0 and UnitTypeId.TEMPEST in self.bot.scouting.known_enemy_composition
    
    @override
    @property
    def custom_conditions(self) -> bool:
        # We never want more than 2 armories
        if (self.amount == 2):
            return False
        
        # We want 1 armory once we have a +1 60% complete
        armory_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.ARMORY)
        upgrades_tech_requirement: float = self.bot.already_pending_upgrade(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
        ebays_count: int = self.bot.structures(UnitTypeId.ENGINEERINGBAY).ready.amount
        if (self.amount == 0):
            return (
                armory_tech_requirement == 1
                and upgrades_tech_requirement >= 0.6
                and self.bot.townhalls.amount >= 3
                and ebays_count >= 1
            )
        
        # We want a second Armory once we have a bunch of mechanical units
        # Vikings so far
        composition: Composition = self.bot.composition_manager.composition
        mechanical_units_amount: int = (
            composition[UnitTypeId.VIKINGFIGHTER]
            + composition[UnitTypeId.LIBERATOR]
            + composition[UnitTypeId.HELLION]
            + composition[UnitTypeId.SIEGETANK]
            + composition[UnitTypeId.THOR]
        )
        if (self.amount == 1):
            return (
                self.bot.expansions.amount_taken >= 4
                and mechanical_units_amount >= 8
            )
    
    @override
    @property
    def position(self) -> Point2:
        expansion: Expansion = self.bot.expansions.taken.random
        if (not expansion):
            return self.bot.expansions.main.position
        units_pool: Units = expansion.mineral_fields + expansion.vespene_geysers
        selected_position: Point2 = units_pool.random.position if units_pool.amount >= 1 else expansion.position
        offset: Point2 = selected_position.negative_offset(expansion.position)
        target: Point2 = selected_position.__add__(offset)
        return selected_position.towards(target, 2)