from typing import override
from bot.buildings.building import Building
from bot.macro.resources import Resources
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class UpgradeBuilding(Building):
    abilityId: AbilityId
    base_building_id: UnitTypeId
   
    @property
    def base_buildings(self) -> Units:
        return self.bot.structures(self.base_building_id).ready.idle
    
    @override
    def on_complete(self):
        print(f'Upgrade {self.name}')
    
    async def upgrade(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        building_cost: Cost = self.bot.calculate_cost(self.abilityId)
        resources_updated: Resources = resources
        for cc in self.base_buildings:
            can_build: bool
            resources_updated: Resources
            can_build, resources_updated = resources.update(building_cost)
            if (can_build == False):
                return resources_updated
            cc(self.abilityId)
            self.on_complete()
        return resources_updated