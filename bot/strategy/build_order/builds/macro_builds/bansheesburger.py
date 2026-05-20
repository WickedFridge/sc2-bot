from typing import override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.addon_swap.detach_swap import AddonDetachSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.build_order_step import BuildOrderStep
from bot.strategy.build_order.builds.macro_build import MacroBuild
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# Build origin
# Cure vs Rogue
# RSL S4 LB SemiFinals, game 3
# https://www.youtube.com/watch?v=We1BrpoLUu8

class BansheesBurger(MacroBuild):
    name: BuildOrderName = BuildOrderName.BANSHEES_BURGER.value

    @override
    def _modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
        elif (self.bot.time <= 300):
            composition.set(UnitTypeId.MARINE, 1)
        if (self.bot.structures(UnitTypeId.STARPORT).amount >= 1):
            composition.set(UnitTypeId.HELLION, 6)
            composition.set(UnitTypeId.BANSHEE, 2)
            composition.set(UnitTypeId.RAVEN, 0)
        return True

    def __init__(self, bot: BotAI):
        super().__init__(bot)
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
            # BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, requirements=[(UnitTypeId.BARRACKS, 3, True)]),
            # BuildOrderStep(bot, self, 'Reactor #3 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=3, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            # BuildOrderStep(bot, self, 'Armory', UnitTypeId.ARMORY, target_count=1, requirements=[(UnitTypeId.FACTORYREACTOR, 1, False), (UnitTypeId.STARPORT, 1, False)]),
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
                    self.bot.composition_manager.should_train(UnitTypeId.BANSHEE) == False
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