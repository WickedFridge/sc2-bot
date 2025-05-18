from typing import override
from bot.buildings.building import Building
from bot.macro.resources import Resources
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class OrbitalCommand(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.ORBITALCOMMAND
        self.abilityId = AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND
        self.name = "Orbital Command"

    @override
    @property
    def conditions(self) -> bool:
        orbital_tech_available: bool = self.bot.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9
        ccs_amount: int = self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle.amount
        return orbital_tech_available and ccs_amount >= 1
    
    async def upgrade(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        building_cost: Cost = self.bot.calculate_cost(self.abilityId)
        resources_updated: Resources = resources
        for cc in self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
            can_build: bool
            resources_updated: Resources
            can_build, resources_updated = resources.update(building_cost)
            if (can_build == False):
                return resources_updated
            print(f'Upgrade {self.name}')
            cc(self.abilityId)
        return resources_updated