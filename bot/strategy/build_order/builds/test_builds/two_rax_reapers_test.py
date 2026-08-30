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

class TwoRaxTest(MacroBuild):
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
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.REFINERY, 1, False)]),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
        ]
        
        self.swap_plans = []