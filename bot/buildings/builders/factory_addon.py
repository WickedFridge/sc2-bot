from typing import override
from bot.buildings.building import Building
from bot.macro.resources import Resources
from bot.utils.matchup import Matchup
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class FactoryAddon(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FACTORYTECHREACTOR
        self.name = "Factory Addon"
        self.radius = 1

    @property
    def factory_without_addon(self) -> Units:
        """Returns factories that are idle and do not have an addon."""
        return self.bot.structures(UnitTypeId.FACTORY).ready.idle.filter(
            lambda factory: not factory.has_add_on and self.bot.in_placement_grid(factory.add_on_position)
        )

    @property
    def next_addon(self) -> UnitTypeId:
        techlab_amount: int = self.bot.structures(UnitTypeId.FACTORYTECHLAB).amount
        reactor_amount: int = self.bot.structures(UnitTypeId.FACTORYREACTOR).amount
        if (techlab_amount == 0):
            return UnitTypeId.FACTORYTECHLAB
        
        reactor_units: list[UnitTypeId] = [
            UnitTypeId.HELLION,
            UnitTypeId.WIDOWMINE,
        ]
        techlab_units: list[UnitTypeId] = [
            UnitTypeId.SIEGETANK,
            UnitTypeId.THOR,
            UnitTypeId.CYCLONE,
        ]
        composition = self.bot.composition_manager.composition
        reactor_units_target: int = sum(composition[unit_type] for unit_type in reactor_units)
        techlab_units_target: int = sum(composition[unit_type] for unit_type in techlab_units)

        MIN_REACTOR_TARGET = 6
        if (reactor_amount == 0 and reactor_units_target < MIN_REACTOR_TARGET):
            return UnitTypeId.FACTORYTECHLAB

        # Équivalent à : reactor_target / (6 * R) > techlab_target / (4 * T)
        # mais sans division, donc sans risque si R == 0
        reactor_pressure: int = reactor_units_target * 4 * techlab_amount
        techlab_pressure: int = techlab_units_target * 6 * reactor_amount

        if (reactor_pressure > techlab_pressure):
            return UnitTypeId.FACTORYREACTOR
        return UnitTypeId.FACTORYTECHLAB
    
    def _factory_info(self) -> tuple[int, int, int, int]:
        starport_amount: int = (
            self.bot.structures(UnitTypeId.STARPORT).ready.amount
            + self.bot.structures(UnitTypeId.STARPORTFLYING).ready.amount
            + int(self.bot.already_pending(UnitTypeId.STARPORT))
        )
        starport_with_reactor_amount: int = self.bot.structures(UnitTypeId.STARPORT).ready.filter(lambda starport: starport.has_add_on).amount
        free_reactors: Units = self.bot.structures(UnitTypeId.REACTOR).ready.filter(
            lambda reactor: self.bot.in_placement_grid(reactor.add_on_land_position)
        )
        return self.factory_without_addon.amount, starport_amount, starport_with_reactor_amount, free_reactors.amount
    
    @property
    @override
    def custom_conditions(self):
        return (
            not self.bot.build_order.build.is_completed
            or self.next_addon == self.unitId
        )
    
    @override
    async def build(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        resources_updated: Resources = resources
        for factory in self.factory_without_addon:
            building_cost: Cost = self.bot.calculate_cost(self.unitId)
            enough_resources: bool
            resources_updated: Resources
            enough_resources, resources_updated = resources_updated.update(building_cost)
            if (enough_resources == False):
                return resources_updated

            factory.build(self.unitId)
            self.on_complete()
        return resources_updated
    
class FactoryReactor(FactoryAddon):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FACTORYREACTOR
        self.name = "Factory Reactor"

class FactoryTechlab(FactoryAddon):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FACTORYTECHLAB
        self.name = "Factory Techlab"