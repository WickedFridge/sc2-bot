from typing import override

from bot.army_composition.composition import Composition
from bot.buildings.addon_swap.swap_plan import SwapPlan
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId


class MacroCyclone(BuildOrder):
    name: BuildOrderName = BuildOrderName.MACRO_CYCLONE.value

    @override
    def modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        # if (self.bot.time <= 300):
        #     composition.set(UnitTypeId.CYCLONE, 2)
        #     return True
        return False

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, False)], workers=21, townhalls=2),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, target_count=1, requirements=[(UnitTypeId.CYCLONE, 1, False)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, target_count=1, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'starport reactor', UnitTypeId.STARPORTREACTOR, target_count=1, requirements=[(UnitTypeId.STARPORT, 1, True)]),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'rax #3', UnitTypeId.BARRACKS, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'rax techlab #1', UnitTypeId.BARRACKSTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, True)]),
            BuildOrderStep(bot, self, 'rax techlab #2', UnitTypeId.BARRACKSTECHLAB, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, True)]),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
        ]

        self.swap_plans = [
            SwapPlan(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.BARRACKSTECHLAB
            ),
        ]