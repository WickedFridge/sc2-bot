from __future__ import annotations

from typing import TYPE_CHECKING, List, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from sc2.ids.upgrade_id import UpgradeId
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId

# Build origin (derived from)
# Clem vs Showtime
# HSC Finals game 2
# https://youtu.be/qYmkoMnToA0?si=czwrxVSwsK4yBo0F&t=828

class DefensiveDoubleCycloneMagfield(BuildOrder):
    name: BuildOrderName = BuildOrderName.DEFENSIVE_DOUBLE_CYCLONE
    is_defensive_response: bool = True
    in_base_cc: bool = False

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
            return True
        else:
            composition.set(UnitTypeId.MARINE, 4)

        if (self.bot.structures(UnitTypeId.STARPORT).ready.amount >= 1):
            composition.set(UnitTypeId.MEDIVAC, 0)
            composition.set(UnitTypeId.VIKINGFIGHTER, 4)

        if (self.bot.structures(UnitTypeId.FACTORY).ready.amount >= 1):
            composition.set(UnitTypeId.CYCLONE, 12)

        return True

    @property
    @override
    def buildings_cut(self) -> List[UnitTypeId]:
        if (
            self.bot.structures([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED]).amount == 1
            and self.bot.structures(UnitTypeId.FACTORY).amount == 0
        ):
            return [UnitTypeId.SUPPLYDEPOT, UnitTypeId.BUNKER]
        if (self.bot.composition_manager.should_train(UnitTypeId.REAPER)):
            return [UnitTypeId.BUNKER]
        return []
    
    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY, target_count=1, townhalls=2),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, workers=18, townhalls=2),
            BuildOrderStep(bot, self, 'barracks techlab', UnitTypeId.BARRACKSTECHLAB, target_count=1, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, workers=22, townhalls=2),
            BuildOrderStep(bot, self, 'factory #2', UnitTypeId.FACTORY, target_count=2, townhalls=2),
            BuildOrderStep(bot, self, 'techlab #2', UnitTypeId.BARRACKSTECHLAB, target_count=2, requirements=[(UnitTypeId.FACTORY, 2, False)]),
            BuildOrderStep(bot, self, 'Magfield', UpgradeId.CYCLONELOCKONDAMAGEUPGRADE, requirements=[(UnitTypeId.FACTORYTECHLAB, 2, True)]),
            BuildOrderStep(bot, self, 'gas #4', UnitTypeId.REFINERY, target_count=4, workers=26, townhalls=2),
            BuildOrderStep(bot, self, 'CC #3', UnitTypeId.COMMANDCENTER, target_count=3, upgrades_required=[UpgradeId.CYCLONELOCKONDAMAGEUPGRADE]),
            BuildOrderStep(bot, self, 'Barracks Reactor', UnitTypeId.BARRACKSREACTOR, townhalls=3),
            BuildOrderStep(bot, self, 'Starport', UnitTypeId.STARPORT, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
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
                UnitTypeId.FACTORY,
                UnitTypeId.TECHLAB,
            ),
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.STARPORT,
                UnitTypeId.REACTOR,
            ),
        ]

