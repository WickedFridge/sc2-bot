from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class ConservativeExpand(BuildOrder):
    name: BuildOrderName = BuildOrderName.CONSERVATIVE_EXPAND.value

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.REFINERY, 1, False)]),
            BuildOrderStep(bot, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, False)]),
            BuildOrderStep(bot, 'reactor', UnitTypeId.BARRACKSREACTOR, townhalls=2, requirements=[(UnitTypeId.MARINE, 1, False)]),
            BuildOrderStep(bot, 'techlab', UnitTypeId.BARRACKSTECHLAB, townhalls=2, requirements=[(UnitTypeId.MARINE, 1, False)]),
            BuildOrderStep(bot, 'rax #3', UnitTypeId.BARRACKS, target_count=3, townhalls=2),
            BuildOrderStep(bot, 'reactor', UnitTypeId.BARRACKSREACTOR, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False), (UnitTypeId.BARRACKSTECHLAB, 1, False)]),
            BuildOrderStep(bot, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, 'facto reactor', UnitTypeId.FACTORYREACTOR, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.FACTORYREACTOR, 1, False)]),
            BuildOrderStep(bot, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.MEDIVAC, 2, False)]),
        ]