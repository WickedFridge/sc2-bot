from __future__ import annotations

from typing import TYPE_CHECKING, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonDetachSwap
from bot.strategy.build_order.addon_swap.addon_swap import AddonSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder, BuildOrderStep
from bot.strategy.build_order.production_queue import ProductionQueue
from bot.utils.unit_tags import techlabs, reactors
from sc2.ids.upgrade_id import UpgradeId
if TYPE_CHECKING:
    from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units

# Build origin (derived from)
# Clem vs Showtime
# HSC Finals game 2
# https://youtu.be/qYmkoMnToA0?si=czwrxVSwsK4yBo0F&t=828

class DefensiveCycloneTank(BuildOrder):
    name: BuildOrderName = BuildOrderName.DEFENSIVE_CYCLONE_TANK
    is_defensive_response: bool = True
    in_base_cc: bool = True

    def __init__(self, bot: Superbot):
        super().__init__(bot)

        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS, requirements=[(UnitTypeId.SUPPLYDEPOT, 1, True)]),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, workers=19, target_count=2, requirements=[(UnitTypeId.BARRACKS, 1, False)]),
            BuildOrderStep(bot, self, 'factory', UnitTypeId.FACTORY),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.REFINERY, 2, False)]),
            BuildOrderStep(bot, self, 'barracks Reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, 'factory techlab', UnitTypeId.FACTORYTECHLAB, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'Starport', UnitTypeId.STARPORT, townhalls=2, requirements=[(UnitTypeId.FACTORYTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.STARPORT, 1, False), (UnitTypeId.STARPORTREACTOR, 2, False)]),
            BuildOrderStep(bot, self, 'rax #2/3', UnitTypeId.BARRACKS, target_count=3, townhalls=3, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, 'Starport techlab', UnitTypeId.STARPORTTECHLAB, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, True)]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, workers=28, townhalls=3, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'Starport Reactor', UnitTypeId.STARPORTREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORTTECHLAB, 2, True)]),
            BuildOrderStep(bot, self, 'factory techlab #3', UnitTypeId.FACTORYTECHLAB, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'double Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, townhalls=3, requirements=[(UnitTypeId.REFINERY, 3, False)]),
            BuildOrderStep(bot, self, 'factory reactor #2', UnitTypeId.FACTORYREACTOR, target_count=3, requirements=[(UnitTypeId.BARRACKSTECHLAB, 3, True)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1]),
            BuildOrderStep(bot, self, 'rax #4/5', UnitTypeId.BARRACKS, target_count=5, requirements=[(UnitTypeId.ENGINEERINGBAY, 2, False)]),
        ]

        self.production_queues = [
            ProductionQueue(
                bot,
                UnitTypeId.BARRACKS,
                [(UnitTypeId.REAPER, 1)],
            ),
            ProductionQueue(
                bot,
                UnitTypeId.FACTORY,
                [(UnitTypeId.CYCLONE, 1), (UnitTypeId.SIEGETANK, 2)],
                hold_until=lambda: self.is_completed,
                hold_composition={ UnitTypeId.CYCLONE: 1, UnitTypeId.SIEGETANK: 2 }
            ),
            ProductionQueue(
                bot,
                UnitTypeId.STARPORT,
                [(UnitTypeId.RAVEN, 1)],
                hold_until=lambda: (
                    self.bot.structures(UnitTypeId.STARPORTREACTOR).amount >= 1
                ),
            ),
        ]
    
        self.swap_plans = [
            AddonDetachSwap(
                bot,
                UnitTypeId.STARPORT,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.RAVEN) == False
                )
            ),
            AddonDetachSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.CYCLONE) == False
                    and self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK) == False
                    and self.bot.structures(techlabs).amount >= 2
                )
            ),
            AddonDetachSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.composition_manager.should_train(UnitTypeId.CYCLONE) == False
                    and self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK) == False
                    and self.bot.structures(techlabs).amount >= 3
                )
            ),
            AddonDetachSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.REACTOR,
                condition=lambda: (
                    self.bot.structures(reactors).amount >= 3
                )
            ),
        ]

