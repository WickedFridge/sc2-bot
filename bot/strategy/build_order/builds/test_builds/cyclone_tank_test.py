from __future__ import annotations

from typing import TYPE_CHECKING, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonDetachSwap
from bot.strategy.build_order.addon_swap.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units

# Test

class CycloneTankTest(BuildOrder):
    name: BuildOrderName = BuildOrderName.TEST
    is_defensive_response: bool = True
    in_base_cc: bool = True

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        modified: bool = False
        if (self.bot.structures(UnitTypeId.FACTORY).ready.amount >= 1):
            modified = True
            factory_units: Units = self.bot.units([UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED])
            if (factory_units.amount == 0):
                composition.set(UnitTypeId.CYCLONE, 1)
                composition.set(UnitTypeId.SIEGETANK, 0)
            else:
                composition.set(UnitTypeId.CYCLONE, 0)
                composition.set(UnitTypeId.SIEGETANK, 2)
        return modified

    def __init__(self, bot: Superbot):
        super().__init__(bot)

        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, workers=19, target_count=2, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY),
            BuildOrderStep(bot, self, 'barracks Reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'factory techlab', UnitTypeId.FACTORYTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
        ]
        
    
        self.swap_plans = []

