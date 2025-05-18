from typing import override
from bot.buildings.building import Building
from bot.macro.resources import Resources
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class BarracksAddon(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKSTECHREACTOR
        self.name = "Barracks Addon"

    @property
    def barracks_without_addon(self) -> Units:
        """Returns barracks that are idle and do not have an addon."""
        return self.bot.structures(UnitTypeId.BARRACKS).ready.idle.filter(
            lambda barrack: not barrack.has_add_on and self.bot.in_placement_grid(barrack.add_on_position)
        )

    @property
    def techlab_count(self) -> int:
        return self.bot.structures(UnitTypeId.BARRACKSTECHLAB).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKSTECHLAB)

    @property
    def reactor_count(self) -> int:
        return self.bot.structures(UnitTypeId.BARRACKSREACTOR).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKSREACTOR)
    
    @property
    def next_addon(self) -> UnitTypeId:
        """Ensures the 2:1 Reactor-to-Techlab ratio is maintained dynamically."""
        if self.techlab_count * 2 < self.reactor_count:
            return UnitTypeId.BARRACKSTECHLAB
        else:
            return UnitTypeId.BARRACKSREACTOR    
    
    @override
    @property
    def conditions(self) -> bool:
        return (
            self.barracks_without_addon.amount >= 1
            and self.next_addon == self.unitId
            and self.bot.units(UnitTypeId.MARINE).amount >= 1
        )

    @override
    async def build(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        resources_updated: Resources = resources
        for barracks in self.barracks_without_addon:
            building_cost: Cost = self.bot.calculate_cost(self.unitId)
            can_build, resources_updated = resources_updated.update(building_cost)

            if (can_build == False):
                continue  # Skip if we can't afford it

            print(f'Build {self.name}')
            barracks.build(self.unitId)
        return resources_updated

class BarracksReactor(BarracksAddon):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKSREACTOR
        self.name = "Barracks Reactor"

class BarracksTechlab(BarracksAddon):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKSTECHLAB
        self.name = "Barracks Techlab"