from typing import override
from bot.buildings.starport_addon import StarportAddon
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class StarportTechlab(StarportAddon):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.STARPORTTECHLAB
        self.name = "Starport Tech Lab"

    @override
    @property
    def custom_conditions(self) -> bool:
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready
        # if we have 2 starports, and one of them doesn't have an addon
        # and we have raven / liberator in our composition
        return (
            starports.amount >= 2
            and self.starports_without_addon.idle.amount >= 1
            and (
                self.bot.composition_manager.composition[UnitTypeId.RAVEN] >= 1
                or self.bot.composition_manager.composition[UnitTypeId.LIBERATOR] >= 1
            )
        )