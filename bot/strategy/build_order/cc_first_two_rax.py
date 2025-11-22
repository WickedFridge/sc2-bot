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
            BuildOrderStep(bot, 'expand', UnitTypeId.COMMANDCENTER),
            BuildOrderStep(bot, 'rax', UnitTypeId.BARRACKS, townhalls=2),
            BuildOrderStep(bot, 'rax #2', UnitTypeId.BARRACKS, townhalls=2),
            BuildOrderStep(bot, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 2, False)]),
            BuildOrderStep(bot, 'reactor', UnitTypeId.BARRACKSREACTOR),
            BuildOrderStep(bot, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, 'gas #2', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False), (UnitTypeId.BARRACKSTECHLAB, 1, False)]),
            BuildOrderStep(bot, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.FACTORYREACTOR, 1, False)]),
            BuildOrderStep(bot, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, 'facto reactor', UnitTypeId.FACTORYREACTOR, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, '3rd CC', UnitTypeId.COMMANDCENTER, requirements=[(UnitTypeId.MEDIVAC, 2, False)]),
        ]