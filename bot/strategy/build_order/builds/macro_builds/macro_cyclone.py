from __future__ import annotations

from typing import TYPE_CHECKING, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.macro_build import MacroBuild
from bot.strategy.build_order.production_queue import ProductionQueue
from bot.strategy.strategy_types import Situation
from sc2.ids.upgrade_id import UpgradeId
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId

# Build origin (derived from)
# Clem vs Showtime
# HSC Finals game 2
# https://youtu.be/qYmkoMnToA0?si=czwrxVSwsK4yBo0F&t=828

class MacroCyclone(MacroBuild):
    name: BuildOrderName = BuildOrderName.MACRO_CYCLONE

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = DefensiveCycloneTank(bot)
        
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, False)], workers=21, townhalls=2),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, True)], townhalls=3),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, target_count=1, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)], townhalls=3),
            BuildOrderStep(bot, self, 'starport reactor', UnitTypeId.STARPORTREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, True)]),
            BuildOrderStep(bot, self, 'rax #2/3', UnitTypeId.BARRACKS, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)], townhalls=3),
            BuildOrderStep(bot, self, 'facto techlab #2', UnitTypeId.FACTORYTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'refinery #3/4', UnitTypeId.REFINERY, target_count=4, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, False)]),
            BuildOrderStep(bot, self, 'rax #4/5', UnitTypeId.BARRACKS, target_count=5, requirements=[(UnitTypeId.REFINERY, 4, False)]),
        ]

        self.production_queues = [
            ProductionQueue(
                bot,
                UnitTypeId.BARRACKS,
                [(UnitTypeId.REAPER, 1)],
            ),
            ProductionQueue(
                bot,
                UnitTypeId.FACTORY,
                [(UnitTypeId.CYCLONE, 1), (UnitTypeId.SIEGETANK, 1)],
                hold_until=lambda: self.is_completed
            ),
        ]
        
        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.FACTORY,
                UnitTypeId.TECHLAB,
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.BARRACKS,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.CYCLONE) == False
                    and self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK) == False
                )
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.BARRACKS,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.CYCLONE) == False
                    and self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK) == False
                    and self.bot.structures(UnitTypeId.BARRACKS).amount >= 3
                )
            )
        ]