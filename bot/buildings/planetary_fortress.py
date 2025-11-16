from typing import override
from bot.buildings.upgrade_building import UpgradeBuilding
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class PlanetaryFortress(UpgradeBuilding):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.PLANETARYFORTRESS
        self.abilityId = AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS
        self.name = "Planetary Fortress"
        self.base_building_id = UnitTypeId.COMMANDCENTER

    @override
    @property
    def base_buildings(self) -> Units:
        return self.bot.structures(self.base_building_id).ready.idle.filter(
            lambda unit: unit.position in self.bot.expansions.positions
        )

    @override
    @property
    def custom_conditions(self) -> bool:
        pf_tech_available: bool = self.bot.tech_requirement_progress(UnitTypeId.PLANETARYFORTRESS) >= 0.9
        townhalls_amount: int = self.bot.townhalls.ready.amount
        if (townhalls_amount <= 3 or not pf_tech_available):
            return False
        if (townhalls_amount >= 4):
            return True