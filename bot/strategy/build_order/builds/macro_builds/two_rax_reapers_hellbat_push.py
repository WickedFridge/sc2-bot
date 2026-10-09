from __future__ import annotations

from typing import TYPE_CHECKING, List, override
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.conservative_rax_expand import ConservativeRaxExpand
from bot.strategy.build_order.builds.macro_build import MacroBuild
from bot.strategy.build_order.production_queue import ProductionQueue
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# Build origin
# Maru vs Reynor
# MOG2 Group A, Decider Match, game 3
# https://youtu.be/Z_vQ5J7ZbcU?t=19442

class TwoRaxReapersHellbatPush(MacroBuild):
    name: BuildOrderName = BuildOrderName.TWO_RAX_REAPERS_HELLBATS

    @property
    @override
    def buildings_cut(self) -> List[UnitTypeId]:
        buildings_cut: List[UnitTypeId] = []
        if (self.bot.townhalls.amount < 3 and self.bot.structures(UnitTypeId.FACTORY).amount < 1):
            buildings_cut.append(UnitTypeId.BUNKER)
        if (self.bot.townhalls.ready.amount < 3 and self.bot.structures([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED]).amount >= 2):
            buildings_cut.append(UnitTypeId.SUPPLYDEPOT)
        return buildings_cut

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = ConservativeRaxExpand(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.REFINERY, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, townhalls=2, workers=20),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, townhalls=2),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, townhalls=3),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, True)]),
            BuildOrderStep(bot, self, 'reactor #2', UnitTypeId.BARRACKSREACTOR, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, True)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.BARRACKSREACTOR, 2, False)]),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, True)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, upgrades_required=[UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, 'gas #3/4', UnitTypeId.REFINERY, target_count=4, requirements=[(UnitTypeId.STARPORT, 1, False)], workers=35),
            BuildOrderStep(bot, self, 'techlab #2 (from facto)', UnitTypeId.FACTORYTECHLAB, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, True)]),
        ]

        self.production_queues = [
            ProductionQueue(
                bot,
                UnitTypeId.BARRACKS,
                [(UnitTypeId.REAPER, 4)],
                hold_until=lambda: (
                    self.unit_amount(UnitTypeId.BARRACKSREACTOR) >= 1
                    and self.unit_amount(UnitTypeId.BARRACKSTECHLAB) >= 1
                    and self.unit_amount(UnitTypeId.FACTORYREACTOR) >= 1
                ),
                hold_composition={UnitTypeId.MARINE: 1},
            ),
            ProductionQueue(
                bot,
                UnitTypeId.FACTORY,
                [(UnitTypeId.HELLION, 4)],
                hold_until=lambda: (
                    self.bot.units_produced(UnitTypeId.MEDIVAC) >= 2
                )
            ),
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