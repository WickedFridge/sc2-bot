from __future__ import annotations

from typing import TYPE_CHECKING, override
from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.conservative_rax_expand import ConservativeRaxExpand
from bot.strategy.build_order.builds.macro_build import MacroBuild
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class TwoRaxReapers(MacroBuild):
    name: BuildOrderName = BuildOrderName.TWO_RAX_REAPERS

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.time <= 150):
            composition.set(UnitTypeId.REAPER, 3)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        return False
    
    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = ConservativeRaxExpand(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.REFINERY, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, True)]),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, townhalls=2),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, townhalls=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, townhalls=2),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False), (UnitTypeId.BARRACKSTECHLAB, 1, False)], townhalls=3),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, self, 'reactor #2 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, False)]),
        ]
        
        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.STARPORT,
                UnitTypeId.REACTOR
            )
        ]