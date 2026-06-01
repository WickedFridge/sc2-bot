from __future__ import annotations

from typing import TYPE_CHECKING, override

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
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# Build origin
# Maru vs Rogue
# RSL S4 LB Finals, game 2
# https://youtu.be/We1BrpoLUu8?si=W0TcQlQs94GcZMVO&t=3539

class Bansheeseburger(MacroBuild):
    name: BuildOrderName = BuildOrderName.BANSHEESEBURGER

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
        elif (self.bot.time <= 300):
            composition.set(UnitTypeId.MARINE, 1)
        if (self.bot.structures(UnitTypeId.STARPORT).amount >= 1):
            composition.set(UnitTypeId.HELLION, 6)
            composition.set(UnitTypeId.BANSHEE, 2)
            composition.set(UnitTypeId.RAVEN, 0)
            if (self.bot.structures(UnitTypeId.STARPORTREACTOR).amount == 0):
                composition.set(UnitTypeId.MEDIVAC, 0)
        return True

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = DefensiveCycloneTank(bot)
        
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)], workers=15),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, army_supply=2, townhalls=2),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'Starport', UnitTypeId.STARPORT, target_count=1, townhalls=3),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, workers=25),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.STARPORT, 1, False), (UnitTypeId.HELLION, 2, False)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, townhalls=3, requirements=[(UnitTypeId.BANSHEE, 1, False)]),
            BuildOrderStep(bot, self, 'techlab #2', UnitTypeId.BARRACKSTECHLAB, target_count=2, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, False)]),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.BANSHEE, 2, False)]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, UpgradeId.TERRANINFANTRYARMORSLEVEL1]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, upgrades_required=[UpgradeId.STIMPACK], workers=40),
            BuildOrderStep(bot, self, 'rax 2/3', UnitTypeId.BARRACKS, target_count=3, upgrades_required=[UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, 'reactor #2 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.FACTORY,
                UnitTypeId.REACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.FACTORY).amount >= 1
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.STARPORT,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORT).amount >= 1
                ),
            ),
            AddonDetachSwap(
                bot,
                UnitTypeId.FACTORY,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORT).ready.amount >= 1
                    and self.bot.composition_manager.should_train(UnitTypeId.HELLION) == False
                ),
            ),
            AddonDetachSwap(
                bot,
                UnitTypeId.STARPORT,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORTTECHLAB).ready.amount >= 1
                    and self.bot.composition_manager.should_train(UnitTypeId.BANSHEE) == False
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.STARPORT,
                UnitTypeId.REACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.FACTORYREACTOR).amount >= 1
                    and self.bot.composition_manager.should_train(UnitTypeId.BANSHEE) == False
                    and self.bot.composition_manager.should_train(UnitTypeId.HELLION) == False
                ),
            ),
        ]