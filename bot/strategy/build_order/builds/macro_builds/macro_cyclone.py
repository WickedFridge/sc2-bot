from typing import override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.macro_build import MacroBuild
from bot.strategy.strategy_types import Situation
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId

# Build origin (derived from)
# Clem vs Showtime
# HSC Finals game 2
# https://youtu.be/qYmkoMnToA0?si=czwrxVSwsK4yBo0F&t=828

class MacroCyclone(MacroBuild):
    name: BuildOrderName = BuildOrderName.MACRO_CYCLONE.value
    cyclone_built: bool = False

    @override
    def _modify_composition(self, composition: Composition) -> None:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        if (self.bot.already_pending(UnitTypeId.CYCLONE) >= 1):
            self.cyclone_built = True
        if (self.bot.structures(UnitTypeId.FACTORYTECHLAB).amount >= 1):
            if (not self.cyclone_built):
                composition.set(UnitTypeId.CYCLONE, 1)
                composition.set(UnitTypeId.SIEGETANK, 0)
            else:
                composition.set(UnitTypeId.CYCLONE, 0)
                composition.set(UnitTypeId.SIEGETANK, 1)
            return True
        return False

    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, False)], workers=21, townhalls=2),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, target_count=1, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)], townhalls=3),
            BuildOrderStep(bot, self, 'starport reactor', UnitTypeId.STARPORTREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, True)]),
            BuildOrderStep(bot, self, 'rax #2/3', UnitTypeId.BARRACKS, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)], townhalls=3),
            BuildOrderStep(bot, self, 'facto techlab #2', UnitTypeId.FACTORYTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
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
                    and self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK) == False
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
                    and self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK) == False
                    and self.bot.structures(UnitTypeId.BARRACKS).amount >= 3
                )
            )
        ]