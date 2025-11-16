from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class KokaBuild(BuildOrder):
    name: BuildOrderName = BuildOrderName.KOKA_BUILD

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, 'reaper', UnitTypeId.REAPER, requirements=[(UnitTypeId.BARRACKS, 1, True)]),
            BuildOrderStep(bot, 'expand', UnitTypeId.COMMANDCENTER, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, 'rax #2', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.BUNKER, 1, False)]),
            BuildOrderStep(bot, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.REAPER, 1, True)]),
            BuildOrderStep(bot, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, 'gas #2', UnitTypeId.REFINERY, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKS, 2, True)]),
            BuildOrderStep(bot, 'starport', UnitTypeId.STARPORT, requirements=[(UnitTypeId.FACTORY, 1, True)]),
            BuildOrderStep(bot, 'facto reactor', UnitTypeId.FACTORYREACTOR, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.FACTORYREACTOR, 1, False)]),
            BuildOrderStep(bot, 'medivac #1', UnitTypeId.MEDIVAC, requirements=[(UnitTypeId.STARPORTREACTOR, 1, True)]),
            BuildOrderStep(bot, 'medivac #2', UnitTypeId.MEDIVAC, requirements=[(UnitTypeId.STARPORTREACTOR, 1, True)]),
            BuildOrderStep(bot, '3rd CC', UnitTypeId.COMMANDCENTER, requirements=[(UnitTypeId.MEDIVAC, 2, False)]),
        ]