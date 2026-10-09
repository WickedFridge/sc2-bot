from __future__ import annotations

from typing import TYPE_CHECKING, List, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.addon_swap.detach_swap import AddonDetachSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.build_order_step import BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.macro_build import MacroBuild
if TYPE_CHECKING:
    from bot.superbot import Superbot
from bot.strategy.build_order.production_queue import ProductionQueue
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# Build origin
# Maru vs Rogue
# RSL S4 LB Finals, game 2
# https://youtu.be/We1BrpoLUu8?si=W0TcQlQs94GcZMVO&t=3539

class Bansheeseburger(MacroBuild):
    name: BuildOrderName = BuildOrderName.BANSHEESEBURGER

    @property
    @override
    def buildings_cut(self) -> List[UnitTypeId]:
        buildings_cut: List[UnitTypeId] = []
        if (self.bot.townhalls.ready.amount < 3 and self.bot.structures([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED]).amount >= 2):
            buildings_cut.append(UnitTypeId.SUPPLYDEPOT)
        return buildings_cut

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = DefensiveCycloneTank(bot)
        
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)], workers=15),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, army_supply=2, townhalls=2),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.FACTORY, 1, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3, requirements=[(UnitTypeId.BARRACKSREACTOR, 1, False)]),
            BuildOrderStep(bot, self, 'Starport', UnitTypeId.STARPORT, target_count=1, townhalls=3),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, workers=25),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.STARPORT, 1, False)]),
            BuildOrderStep(bot, self, '2 Ebays', UnitTypeId.ENGINEERINGBAY, target_count=2, townhalls=3, requirements=[(UnitTypeId.BANSHEE, 1, False)]),
            BuildOrderStep(bot, self, 'techlab #2', UnitTypeId.BARRACKSTECHLAB, target_count=2, requirements=[(UnitTypeId.BANSHEE, 1, False)]),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1], requirements=[(UnitTypeId.BANSHEE, 2, False)]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, workers=38),
            BuildOrderStep(bot, self, 'rax 2/3', UnitTypeId.BARRACKS, target_count=3, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, UpgradeId.TERRANINFANTRYARMORSLEVEL1], workers=39),
            BuildOrderStep(bot, self, 'reactor #2 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.BARRACKS, 2, False), (UnitTypeId.BANSHEE, 2, False)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, UpgradeId.TERRANINFANTRYARMORSLEVEL1]),
            BuildOrderStep(bot, self, 'reactor #3 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=3, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'reactor #4 (from starport)', UnitTypeId.FACTORYREACTOR, target_count=4, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'rax 4/5', UnitTypeId.BARRACKS, target_count=5, upgrades_required=[UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, 'gas #4', UnitTypeId.REFINERY, target_count=3, workers=44, requirements=[(UnitTypeId.BARRACKS, 5, False)]),

        ]

        self.production_queues = [
            ProductionQueue(
                bot,
                UnitTypeId.BARRACKS,
                [(UnitTypeId.REAPER, 1)],
                hold_until=lambda: (
                    self.bot.already_pending(UpgradeId.STIMPACK) > 0
                ),
                hold_composition={UnitTypeId.MARINE: 1},
            ),
            ProductionQueue(
                bot,
                UnitTypeId.FACTORY,
                [(UnitTypeId.HELLION, 6)],
                start_when=lambda: (
                    self.bot.structures(UnitTypeId.STARPORT).amount >= 1
                ),
            ),
            ProductionQueue(
                bot,
                UnitTypeId.STARPORT,
                [(UnitTypeId.BANSHEE, 2)],
                hold_until=lambda: (
                    self.bot.structures(UnitTypeId.STARPORTREACTOR).amount >= 1
                ),
            ),
        ]

        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.FACTORY,
                UnitTypeId.REACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.FACTORY).amount >= 1
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.BARRACKS,
                UnitTypeId.STARPORT,
                UnitTypeId.TECHLAB,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORT).amount >= 1
                ),
            ),
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.BARRACKS,
                UnitTypeId.REACTOR,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.FACTORYREACTOR).amount >= 1
                    and self.bot.structures(UnitTypeId.BARRACKS).amount >= 2
                    and self.bot.composition_manager.should_train(UnitTypeId.HELLION) == False
                ),
            ),
            AddonDetachSwap(
                bot,
                UnitTypeId.STARPORT,
                condition=lambda: (
                    self.bot.structures(UnitTypeId.STARPORTTECHLAB).amount >= 1
                    and self.bot.composition_manager.should_train(UnitTypeId.BANSHEE) == False
                ),
            ),
            
        ]