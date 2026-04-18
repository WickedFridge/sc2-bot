from typing import List, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.addon_swap.detach_swap import AddonDetachSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.macro_build import MacroBuild
from bot.strategy.strategy_types import Situation
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# build origin
# Byun vs Ryung
# Wardi Team League Day 2, game 5
# https://www.twitch.tv/videos/2720329129?t=02h42m37s

class Cyclone3Raven(MacroBuild):
    name: BuildOrderName = BuildOrderName.CYCLONE_3_RAVEN.value
    cyclone_built: bool = False

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.structures(UnitTypeId.STARPORTREACTOR).amount == 0):
            composition.set(UnitTypeId.MEDIVAC, 0)
        if (self.bot.structures(UnitTypeId.STARPORTTECHLAB).amount == 1):
            composition.set(UnitTypeId.RAVEN, 3)
        if (self.bot.structures(UnitTypeId.BARRACKSREACTOR).amount == 0):
            composition.set(UnitTypeId.MARINE, 0)
            composition.set(UnitTypeId.REAPER, 2)
        composition.set(UnitTypeId.HELLION, 2)
        if (self.bot.units(UnitTypeId.CYCLONE).amount >= 1):
            self.cyclone_built = True
        if (not self.cyclone_built):
            composition.set(UnitTypeId.CYCLONE, 1)
            composition.set(UnitTypeId.SIEGETANK, 0)
        else:
            composition.set(UnitTypeId.CYCLONE, 0)
        return True

    @override
    @property
    def buildings_cut(self) -> List[UnitTypeId]:
        if (
            self.bot.structures([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED]).amount == 1
            and self.bot.structures(UnitTypeId.FACTORY).amount == 0
        ):
            return [UnitTypeId.SUPPLYDEPOT, UnitTypeId.BUNKER]
        if (self.bot.composition_manager.should_train(UnitTypeId.REAPER)):
            return [UnitTypeId.BUNKER]
        return []
    
    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, False)]),
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, requirements=[(UnitTypeId.FACTORY, 1, False)], workers=19, townhalls=2),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, self, 'rax techlab', UnitTypeId.BARRACKSTECHLAB, target_count=1, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, False)], workers=23),
            BuildOrderStep(bot, self, 'rax reactor', UnitTypeId.BARRACKSREACTOR, target_count=1, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'factory techlab', UnitTypeId.FACTORYTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.FACTORYTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, townhalls=3),
            BuildOrderStep(bot, self, 'starport reactor', UnitTypeId.STARPORTREACTOR, target_count=2, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, False)]),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.STARPORTREACTOR, 1, False)], townhalls=3),
            BuildOrderStep(bot, self, 'rax #3', UnitTypeId.BARRACKS, target_count=3, requirements=[(UnitTypeId.STARPORTREACTOR, 1, False)], townhalls=3),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.BARRACKSFLYING,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                UnitTypeId.BARRACKSTECHLAB
            ),
            AddonDetachSwap(
                bot,
                UnitTypeId.STARPORT,
                UnitTypeId.STARPORTFLYING,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.RAVEN) == False
                )
            ),
        ]