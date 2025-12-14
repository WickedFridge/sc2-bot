from typing import override
from bot.army_composition.composition import Composition
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class KokaBuild(BuildOrder):
    name: BuildOrderName = BuildOrderName.KOKA_BUILD.value

    @override
    def modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        return False

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, 'rax', UnitTypeId.BARRACKS),
            BuildOrderStep(bot, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)], workers=15),
            # BuildOrderStep(bot, 'reaper', UnitTypeId.REAPER, requirements=[(UnitTypeId.BARRACKS, 1, True)]),
            BuildOrderStep(bot, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, 'rax #2', UnitTypeId.BARRACKS, target_count=2, townhalls=2),
            BuildOrderStep(bot, 'reactor', UnitTypeId.BARRACKSREACTOR, army_supply=1),
            BuildOrderStep(bot, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, False)], workers=21, townhalls=2),
            BuildOrderStep(bot, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKS, 2, True)]),
            BuildOrderStep(bot, 'starport', UnitTypeId.STARPORT, requirements=[(UnitTypeId.FACTORY, 1, True)]),
            BuildOrderStep(bot, 'facto reactor', UnitTypeId.FACTORYREACTOR, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.FACTORYREACTOR, 1, False)]),
            # BuildOrderStep(bot, 'medivac #1', UnitTypeId.MEDIVAC, target_count=1, requirements=[(UnitTypeId.STARPORTREACTOR, 1, True)]),
            # BuildOrderStep(bot, 'medivac #2', UnitTypeId.MEDIVAC, target_count=2, requirements=[(UnitTypeId.STARPORTREACTOR, 1, True)]),
            BuildOrderStep(bot, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.MEDIVAC, 2, False)]),
        ]