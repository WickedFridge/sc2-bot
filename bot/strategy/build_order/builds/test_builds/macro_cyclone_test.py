from __future__ import annotations

from typing import TYPE_CHECKING, List, override
from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrderStep
from bot.strategy.build_order.builds.macro_build import MacroBuild
if TYPE_CHECKING:
    from bot.superbot import Superbot
from bot.strategy.build_order.builds.test_builds.cyclone_tank_test import CycloneTankTest
from sc2.ids.unit_typeid import UnitTypeId

# Test

class CycloneTest(MacroBuild):
    name: BuildOrderName = BuildOrderName.TEST

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        return False
    
    @property
    @override
    def buildings_cut(self) -> List[UnitTypeId]:
        if (self.bot.townhalls.amount < 3):
            return [UnitTypeId.BUNKER]
        return []

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = CycloneTankTest(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, workers=19, target_count=2, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'barracks reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORYTECHLAB, 1, False)]),
        ]
        
        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.FACTORY,
                UnitTypeId.TECHLAB,
            ),
        ]