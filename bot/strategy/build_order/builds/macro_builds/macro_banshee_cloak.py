from __future__ import annotations

from typing import TYPE_CHECKING, List, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.addon_swap.detach_swap import AddonDetachSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.build_order_step import BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.macro_build import MacroBuild
if TYPE_CHECKING:
    from bot.superbot import Superbot
from bot.strategy.build_order.production_queue import ProductionQueue
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# Build origin
# Maru vs Classic
# Mog2 Semifinals winner, game 2
# https://youtu.be/1uk90hS7Z5M?t=1256

class BansheeCloakMarineTank(MacroBuild):
    name: BuildOrderName = BuildOrderName.BANSHEE_CLOAK_MARINE_TANK

    @property
    @override
    def buildings_cut(self) -> List[UnitTypeId]:
        if (
            self.bot.structures([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED]).amount == 1
            and self.bot.structures(UnitTypeId.FACTORY).amount == 0
        ):
            return [UnitTypeId.SUPPLYDEPOT, UnitTypeId.BUNKER]
        if (self.bot.composition_manager.should_train(UnitTypeId.REAPER)):
            return [UnitTypeId.BUNKER]
        return []

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = DefensiveCycloneTank(bot)
        
        self.steps = [
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, False)]),
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, False)], workers=19, townhalls=2),
            BuildOrderStep(bot, self, 'rax reactor', UnitTypeId.BARRACKSREACTOR, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT),
            
        ]

        self.production_queues = [
            ProductionQueue(
                bot,
                UnitTypeId.BARRACKS,
                [(UnitTypeId.REAPER, 1)],
            ),
            # ProductionQueue(
            #     bot,
            #     UnitTypeId.FACTORY,
            #     [(UnitTypeId.HELLION, 6)],
            #     start_when=lambda: (
            #         self.bot.structures(UnitTypeId.STARPORT).amount >= 1
            #     ),
            # ),
            # ProductionQueue(
            #     bot,
            #     UnitTypeId.STARPORT,
            #     [(UnitTypeId.BANSHEE, 2)],
            #     hold_until=lambda: (
            #         self.bot.structures(UnitTypeId.STARPORTREACTOR).amount >= 1
            #     ),
            # ),
        ]

        self.swap_plans = [
            # AddonSwap(
            #     bot,
            #     UnitTypeId.BARRACKS,
            #     UnitTypeId.FACTORY,
            #     UnitTypeId.REACTOR,
            # ),
            # AddonSwap(
            #     bot,
            #     UnitTypeId.BARRACKS,
            #     UnitTypeId.STARPORT,
            #     UnitTypeId.TECHLAB,
            # ),
            # AddonDetachSwap(
            #     bot,
            #     UnitTypeId.FACTORY,
            #     UnitTypeId.REACTOR,
            #     condition=lambda: (
            #         self.bot.composition_manager.should_train(UnitTypeId.HELLION) == False
            #     ),
            # ),
            # AddonDetachSwap(
            #     bot,
            #     UnitTypeId.STARPORT,
            #     UnitTypeId.TECHLAB,
            #     condition=lambda: (
            #         self.bot.composition_manager.should_train(UnitTypeId.BANSHEE) == False
            #     ),
            # ),
            
        ]