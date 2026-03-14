from typing import override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId

# Build origin (derived from)
# Clem vs Showtime
# HSC Finals game 2
# https://youtu.be/qYmkoMnToA0?si=czwrxVSwsK4yBo0F&t=828

class DefensiveCyclone(BuildOrder):
    name: BuildOrderName = BuildOrderName.DEFENSIVE_CYCLONE.value

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
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.REFINERY, 2, False)]),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.CYCLONE, 1, False)]),
            BuildOrderStep(bot, self, 'rax #2/3', UnitTypeId.BARRACKS, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'starport reactor', UnitTypeId.STARPORTREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, True)]),
            BuildOrderStep(bot, self, 'facto techlab #2', UnitTypeId.FACTORYTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.BARRACKSTECHLAB
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.FACTORYTECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.CYCLONE) == False
                )
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.FACTORYFLYING,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.FACTORYTECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.CYCLONE) == False
                    and self.bot.structures(UnitTypeId.BARRACKS).amount >= 3
                )
            ),
        ]