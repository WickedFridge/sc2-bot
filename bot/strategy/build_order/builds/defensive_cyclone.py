from typing import override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId


class DefensiveCyclone(BuildOrder):
    name: BuildOrderName = BuildOrderName.DEFENSIVE_CYCLONE.value

    @override
    def modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        if (self.bot.time <= 240):
            composition.set(UnitTypeId.CYCLONE, 1)
            return True
        return False

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2),
            BuildOrderStep(bot, 'factory techlab', UnitTypeId.FACTORYTECHLAB, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.FACTORYTECHLAB, 1, False)], workers=21, townhalls=2),
            BuildOrderStep(bot, 'starport', UnitTypeId.STARPORT, target_count=1, requirements=[(UnitTypeId.CYCLONE, 1, False)]),
            BuildOrderStep(bot, 'reactor', UnitTypeId.BARRACKSREACTOR, target_count=1, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, 'rax #3', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
        ]