from __future__ import annotations

from typing import TYPE_CHECKING, List, override

from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.macro_build import MacroBuild
from bot.strategy.build_order.production_queue import ProductionQueue
from sc2.ids.upgrade_id import UpgradeId
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId

# Build origin (derived from)
# Cure vs herO
# 2026 GSL S1 Ro.4 g1
# https://youtu.be/OTuriH2kyYY?t=1192

class MacroConcussive(MacroBuild):
    name: BuildOrderName = BuildOrderName.MACRO_CONCUSSIVE

    @property
    @override
    def buildings_cut(self) -> List[UnitTypeId]:
        if (not self.bot.upgrade_started(UpgradeId.PUNISHERGRENADES)):
            return [UnitTypeId.BUNKER]
        return []

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = DefensiveCycloneTank(bot)
        
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, workers=19, townhalls=2),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, target_count=1, townhalls=2, units_produced_required=[(UnitTypeId.REAPER, 1)]),
            BuildOrderStep(bot, self, 'concussive', UpgradeId.PUNISHERGRENADES, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2, upgrades_required=[UpgradeId.PUNISHERGRENADES]),
            BuildOrderStep(bot, self, 'Ebay #1', UnitTypeId.ENGINEERINGBAY, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'barracks reactor', UnitTypeId.BARRACKSREACTOR, target_count=1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, False)]),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1], requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)], townhalls=2),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKS, 2, False)]),
            BuildOrderStep(bot, self, 'rax #3', UnitTypeId.BARRACKS, target_count=3, townhalls=3),
            BuildOrderStep(bot, self, 'refinery #3', UnitTypeId.REFINERY, target_count=3, townhalls=3, workers=40),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, True)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.BARRACKSTECHLAB, 2, False)]),
            BuildOrderStep(bot, self, 'shield', UpgradeId.SHIELDWALL, upgrades_required=[UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, target_count=1, requirements=[(UnitTypeId.BARRACKS, 3, False)], upgrades_required=[UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, 'facto reactor', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, 'rax #4-5', UnitTypeId.BARRACKS, target_count=5, requirements=[(UnitTypeId.STARPORT, 1, False)]),
        ]

        self.production_queues = [
            ProductionQueue(
                bot,
                UnitTypeId.BARRACKS,
                [(UnitTypeId.REAPER, 1), (UnitTypeId.MARAUDER, 2)],
            ),
            ProductionQueue(
                bot,
                UnitTypeId.FACTORY,
                [(UnitTypeId.CYCLONE, 1), (UnitTypeId.SIEGETANK, 2)],
            ),
            ProductionQueue(
                bot,
                UnitTypeId.STARPORT,
                [(UnitTypeId.MEDIVAC, 2)],
                start_when=lambda: (self.bot.structures(UnitTypeId.STARPORTREACTOR).amount >= 1)
            ),
        ]
        
        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.FACTORY,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.MARAUDER) == False
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
                )
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.STARPORT,
                UnitTypeId.REACTOR,
            )
        ]