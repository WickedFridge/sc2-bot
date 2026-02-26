from typing import override

from bot.buildings.addon_swap.swap_plan import SwapPlan
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class Dummybuild(BuildOrder):
    name: BuildOrderName = BuildOrderName.DUMMY_BUILD.value

    @override
    def modify_composition(self, composition):
        pass
        # composition.set(UnitTypeId.MEDIVAC, 0)

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, self, 'facto reactor', UnitTypeId.FACTORYREACTOR, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            # BuildOrderStep(bot, self, 'reaper', UnitTypeId.REAPER, requirements=[(UnitTypeId.BARRACKS, 1, True)]),
            # BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.BARRACKS, 1, True)]),
            # BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, townhalls=2),
            # BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            # BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, False)]),
        ]
        
        self.swap_plans: list[SwapPlan] = [
            SwapPlan(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                UnitTypeId.FACTORYREACTOR
            )
        ]