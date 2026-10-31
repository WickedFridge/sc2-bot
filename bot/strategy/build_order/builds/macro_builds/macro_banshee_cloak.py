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
from bot.utils.unit_tags import techlabs

# Build origin
# Maru vs Classic
# Mog2 Semifinals winner, game 2
# https://youtu.be/1uk90hS7Z5M?t=1256

class BansheeCloak3CC(MacroBuild):
    name: BuildOrderName = BuildOrderName.BANSHEE_CLOAK_3CC
    is_defensive_response = True

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
            BuildOrderStep(bot, self, 'facto techlab', UnitTypeId.FACTORYTECHLAB, target_count=1, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, 'facto techlab #2', UnitTypeId.FACTORYTECHLAB, target_count=2, requirements=[(UnitTypeId.TECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'cloak', UpgradeId.BANSHEECLOAK, target_count=1, requirements=[(UnitTypeId.STARPORTTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, workers=27, townhalls=2),
            BuildOrderStep(bot, self, 'rax #2/3', UnitTypeId.BARRACKS, target_count=3, upgrades_required=[UpgradeId.BANSHEECLOAK]),
            BuildOrderStep(bot, self, 'ebay', UnitTypeId.ENGINEERINGBAY, target_count=1, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'Starport reactor', UnitTypeId.STARPORTREACTOR, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'shield', UpgradeId.SHIELDWALL, requirements=[(UnitTypeId.BARRACKSTECHLAB, 2, True)]),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, upgrades_required=[UpgradeId.STIMPACK, UpgradeId.SHIELDWALL, UpgradeId.TERRANINFANTRYARMORSLEVEL1]),
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
                start_when=lambda: (
                    self.bot.already_pending_upgrade(UpgradeId.BANSHEECLOAK) > 0
                ),
                hold_until=lambda: self.is_completed
            ),
            ProductionQueue(
                bot,
                UnitTypeId.STARPORT,
                [(UnitTypeId.BANSHEE, 2)],
                hold_until=lambda: (
                    self.bot.structures(UnitTypeId.STARPORTREACTOR).amount >= 1
                ),
            ),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.STARPORT,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.structures(techlabs).amount == 1
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.BARRACKS,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.BARRACKS).amount >= 2
                    and self.bot.already_pending_upgrade(UpgradeId.BANSHEECLOAK) > 0
                    and self.bot.composition_manager.should_train(UnitTypeId.CYCLONE) == False
                    and self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK) == False
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.STARPORT,
                UnitTypeId.BARRACKS,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.BANSHEE) == False
                ),
            ),
        ]