from __future__ import annotations

from typing import TYPE_CHECKING, List, override
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

# Build origin
# Maru vs Rogue
# 2026 GSL S1 RO8 Group A, Match 2, game 3
# https://www.youtube.com/watch?v=bZGOZIRCTU4

class TwoRaxReapersKokabuild(MacroBuild):
    name: BuildOrderName = BuildOrderName.TWO_RAX_REAPERS_KOKABUILD

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.time <= 150):
            composition.set(UnitTypeId.REAPER, 3)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        return False
    
    @override
    @property
    def buildings_cut(self) -> List[UnitTypeId]:
        if (self.bot.townhalls.amount < 3):
            return [UnitTypeId.BUNKER]
        return []

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
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, townhalls=2),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, upgrades_required=[UpgradeId.STIMPACK], townhalls=3),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, requirements=[(UnitTypeId.FACTORY, 1, False)], workers=31),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, self, 'reactor #2 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, False), (UnitTypeId.FACTORYREACTOR, 2, False)]),
            BuildOrderStep(bot, self, 'combat shield', UpgradeId.SHIELDWALL, upgrades_required=[UpgradeId.STIMPACK]),
        ]
        
        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.STARPORT,
                UnitTypeId.REACTOR
            )
        ]