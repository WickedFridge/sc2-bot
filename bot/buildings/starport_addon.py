from typing import override
from bot.buildings.building import Building
from bot.macro.resources import Resources
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class StarportAddon(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.STARPORTTECHREACTOR
        self.name = "Starport Addon"

    @property
    def starports_without_addon(self) -> Units:
        """Returns starports that are idle and do not have an addon."""
        return self.bot.structures(UnitTypeId.STARPORT).ready.idle.filter(
            lambda starport: not starport.has_add_on and self.bot.in_placement_grid(starport.add_on_position)
        )

    
    @override
    async def build(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        resources_updated: Resources = resources
        for starport in self.starports_without_addon.idle:
            building_cost: Cost = self.bot.calculate_cost(self.unitId)
            can_build, resources_updated = resources_updated.update(building_cost)

            if (can_build == False):
                continue
            
            starport.build(self.unitId)
            self.on_complete()
        return resources_updated