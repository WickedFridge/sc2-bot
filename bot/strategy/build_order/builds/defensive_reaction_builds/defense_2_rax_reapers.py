from __future__ import annotations

from typing import TYPE_CHECKING, override
from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class DefensiveTwoRax(BuildOrder):
    name: BuildOrderName = BuildOrderName.DEFENSIVE_TWO_RAX
    in_base_cc: bool = True
    cyclone_built: bool = False

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.time <= 150):
            composition.set(UnitTypeId.REAPER, 3)
            composition.set(UnitTypeId.MARINE, 0)
        
        if (self.bot.units(UnitTypeId.CYCLONE).amount >= 1):
            self.cyclone_built = True
        if (not self.cyclone_built):
            composition.set(UnitTypeId.CYCLONE, 1)
            composition.set(UnitTypeId.SIEGETANK, 0)
        else:
            composition.set(UnitTypeId.CYCLONE, 0)
            
        if (self.bot.structures(UnitTypeId.STARPORTTECHLAB).amount == 1):
            composition.set(UnitTypeId.RAVEN, 2)
            composition.set(UnitTypeId.MEDIVAC, 0)
        return True
    
    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'rax #2', UnitTypeId.BARRACKS, target_count=2, requirements=[(UnitTypeId.REFINERY, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, False)]),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, townhalls=2),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, townhalls=2),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, townhalls=2, workers=21),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False), (UnitTypeId.BARRACKSTECHLAB, 1, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT, townhalls=3),
            BuildOrderStep(bot, self, 'techlab #2', UnitTypeId.BARRACKSTECHLAB, target_count=2, townhalls=3, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, townhalls=3, workers=33),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, requirements=[(UnitTypeId.BARRACKSTECHLAB, 2, True)]),
            BuildOrderStep(bot, self, 'rax #3', UnitTypeId.BARRACKS, target_count=3, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, False)]),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, True)]),
            BuildOrderStep(bot, self, 'reactor #2', UnitTypeId.BARRACKSREACTOR, target_count=2, requirements=[(UnitTypeId.BARRACKSTECHLAB, 2, True)]),
            BuildOrderStep(bot, self, 'reactor #3', UnitTypeId.STARPORTREACTOR, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, True)]),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.FACTORY,
                UnitTypeId.TECHLAB,
            ),
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.STARPORT,
                UnitTypeId.TECHLAB,
            ),
            AddonSwap(
                bot,
                UnitTypeId.STARPORT,
                UnitTypeId.BARRACKS,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORTTECHLAB).ready.amount >= 1
                    and self.bot.composition_manager.should_train(UnitTypeId.RAVEN) == False
                )
            ),
        ]