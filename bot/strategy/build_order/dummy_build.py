from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId


class Dummybuild(BuildOrder):
    name: BuildOrderName = BuildOrderName.DUMMY_BUILD.value

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, False)]),
            BuildOrderStep(bot, 'rax', UnitTypeId.BARRACKS),
            BuildOrderStep(bot, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, 'factory', UnitTypeId.FACTORY),
            BuildOrderStep(bot, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, 'facto reactor', UnitTypeId.FACTORYREACTOR, requirements=[(UnitTypeId.STARPORT, 1, False)]),
        ]