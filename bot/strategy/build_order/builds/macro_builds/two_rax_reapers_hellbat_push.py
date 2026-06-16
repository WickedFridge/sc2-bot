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
# Maru vs Reynor
# MOG2 Group A, Decider Match, game 3
# https://www.twitch.tv/videos/2786886731?t=05h25m52s

class TwoRaxReapersHellbatPush(MacroBuild):
    name: BuildOrderName = BuildOrderName.TWO_RAX_REAPERS_HELLBATS

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.time <= 180):
            composition.set(UnitTypeId.REAPER, 4)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        if (self.bot.time <= 280):
            composition.set(UnitTypeId.HELLION, 4)
            composition.set(UnitTypeId.MARINE, 1)
            return True
        return False
    
    @property
    @override
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
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, townhalls=2, workers=20),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, townhalls=2),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, townhalls=3),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, True)]),
            BuildOrderStep(bot, self, 'reactor #2', UnitTypeId.BARRACKSREACTOR, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, True)]),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, True)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, UpgradeId.TERRANINFANTRYARMORSLEVEL1]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, upgrades_required=[UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, 'gas #3/4', UnitTypeId.REFINERY, target_count=4, requirements=[(UnitTypeId.STARPORT, 1, False)], workers=35),
            BuildOrderStep(bot, self, 'techlab #2 (from facto)', UnitTypeId.FACTORYTECHLAB, target_count=2, requirements=[(UnitTypeId.REFINERY, 4, False)]),
        ]
        
        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.FACTORY,
                UnitTypeId.REACTOR
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.STARPORT,
                UnitTypeId.REACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORT).amount >= 1
                    and self.bot.composition_manager.should_train(UnitTypeId.HELLION) == False
                ),
            )
        ]