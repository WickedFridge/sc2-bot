from typing import List, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class DefensiveMistral211(BuildOrder):
    name: BuildOrderName = BuildOrderName.DEFENSIVE_MISTRAL_211.value
    in_base_cc: bool = True

    @override
    def _modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        if (
            self.bot.structures(UnitTypeId.FACTORY).amount == 1
            and self.bot.structures(UnitTypeId.STARPORT).amount == 0
        ):
            composition.set(UnitTypeId.HELLION, 3)
        if (self.bot.structures(UnitTypeId.STARPORTREACTOR).amount == 0):
            composition.set(UnitTypeId.MEDIVAC, 0)
        composition.set(UnitTypeId.CYCLONE, 0)
        return True

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, False)]),
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.REFINERY, 1, False)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.MARINE, 1, False), (UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, townhalls=2),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, townhalls=2),
            BuildOrderStep(bot, self, 'factory techlab', UnitTypeId.FACTORYTECHLAB, requirements=[(UnitTypeId.STARPORT, 1, False), (UnitTypeId.HELLION, 1, True)]),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, townhalls=2, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, 'factory reactor #2', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, False)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.MEDIVAC, 2, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.MEDIVAC, 2, False)]),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                UnitTypeId.FACTORYTECHLAB,
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                UnitTypeId.FACTORYREACTOR,
            ),
            AddonSwap(
                bot,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.STARPORTTECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.RAVEN) == False
                    and self.bot.structures([
                        UnitTypeId.REACTOR,
                        UnitTypeId.BARRACKSREACTOR,
                        UnitTypeId.FACTORYREACTOR,
                        UnitTypeId.STARPORTREACTOR
                    ]).amount == 2
                )
            ),
        ]