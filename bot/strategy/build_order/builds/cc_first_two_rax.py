from bot.buildings.addon_swap.swap_plan import SwapPlan
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class CCFirstTwoRax(BuildOrder):
    name: BuildOrderName = BuildOrderName.CC_FIRST_TWO_RAX.value

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2),
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, townhalls=2),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, townhalls=2),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 2, False)]),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False), (UnitTypeId.BARRACKSTECHLAB, 1, False)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, self, 'facto reactor', UnitTypeId.FACTORYREACTOR, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.FACTORYREACTOR, 1, False)]),
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