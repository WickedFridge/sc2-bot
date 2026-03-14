from typing import override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.addon_swap.detach_swap import AddonDetachSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.build_order_step import BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# Build origin
# Clem vs Reynor
# Big gabe XperionCraft 3 Finals, game 4
# https://youtu.be/xwjKSOqq10s?si=R7U2CDLfLFwbONGY&t=2759

class Greedy22Timing(BuildOrder):
    name: BuildOrderName = BuildOrderName.GREEDY_2_2_TIMING.value

    @override
    def modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        if (self.bot.time <= 240):
            composition.set(UnitTypeId.MARINE, 1)
            composition.set(UnitTypeId.HELLION, 4)
            return True
        return False

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)], workers=15),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, army_supply=2, townhalls=2),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, townhalls=3, requirements=[(UnitTypeId.HELLION, 2, False)]),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, workers=28),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, True)]),
            BuildOrderStep(bot, self, 'Rax 2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, True)]),
            BuildOrderStep(bot, self, 'Rax 3', UnitTypeId.BARRACKS, target_count=3, upgrades_required=[UpgradeId.TERRANINFANTRYARMORSLEVEL1]),
            BuildOrderStep(bot, self, 'Reactor #2 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.FACTORYREACTOR, 2, False)]),
            BuildOrderStep(bot, self, 'gas #3/4', UnitTypeId.REFINERY, target_count=4, upgrades_required=[UpgradeId.STIMPACK], workers=28),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, requirements=[(UnitTypeId.BARRACKS, 3, True)]),
            BuildOrderStep(bot, self, 'Reactor #3 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=3, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, 'Armory', UnitTypeId.ARMORY, target_count=1, requirements=[(UnitTypeId.FACTORYREACTOR, 1, False), (UnitTypeId.STARPORT, 1, False)]),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.BARRACKSREACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.FACTORY).amount >= 1
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.FACTORYREACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.BARRACKS).amount >= 2
                    and self.bot.composition_manager.should_train(UnitTypeId.HELLION) == False
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.FACTORYREACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.BARRACKS).amount >= 3
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                UnitTypeId.FACTORYREACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORT).amount >= 1
                ),
            )
        ]