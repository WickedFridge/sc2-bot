from __future__ import annotations

from typing import TYPE_CHECKING, Optional, override

from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonSwap
from bot.strategy.build_order.addon_swap.detach_swap import AddonDetachSwap
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.build_order_step import BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.conservative_rax_expand import ConservativeRaxExpand
from bot.strategy.build_order.builds.macro_build import MacroBuild
from bot.utils.army import Army
if TYPE_CHECKING:
    from bot.superbot import Superbot
from bot.strategy.build_order.production_queue import ProductionQueue
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# Build origin
# Maru vs trigger
# Mog 2 Group A, Decider Match, game 2
# https://youtu.be/Z_vQ5J7ZbcU?t=15159

class ThreeCC5RaxPlus1(MacroBuild):
    name: BuildOrderName = BuildOrderName.THREECC_5RAX_PLUS_1

    @override
    def _modify_composition(self, composition: Composition) -> bool:
        if (self.bot.already_pending_upgrade(UpgradeId.SHIELDWALL) > 0):
            composition.add(UnitTypeId.MARAUDER, 10)
            return True
        return False

    @override
    def is_army_ready_to_attack(self, army: Army) -> Optional[bool]:
        return (
            self.bot.supply_army >= 30
            and self.bot.already_pending_upgrade(UpgradeId.STIMPACK) >= 0.9
            and self.bot.already_pending_upgrade(UpgradeId.SHIELDWALL) >= 0.85
            and self.bot.already_pending_upgrade(UpgradeId.PUNISHERGRENADES) >= 0.5
            and self.bot.already_pending_upgrade(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1) >= 0.9
        )
    
    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = ConservativeRaxExpand(bot)
        
        self.steps = [
            BuildOrderStep(bot, self, 'rax', UnitTypeId.BARRACKS),
            BuildOrderStep(bot, self, 'gas', UnitTypeId.REFINERY, requirements=[(UnitTypeId.BARRACKS, 1, False)], workers=15),
            BuildOrderStep(bot, self, 'expand', UnitTypeId.COMMANDCENTER, target_count=2, requirements=[(UnitTypeId.ORBITALCOMMAND, 1, False)]),
            BuildOrderStep(bot, self, 'reactor', UnitTypeId.BARRACKSREACTOR, requirements=[(UnitTypeId.MARINE, 2, False)]),
            BuildOrderStep(bot, self, '3rd CC', UnitTypeId.COMMANDCENTER, target_count=3),
            BuildOrderStep(bot, self, 'Rax 2/3', UnitTypeId.BARRACKS, target_count=3, townhalls=3),
            BuildOrderStep(bot, self, 'Ebay #1', UnitTypeId.ENGINEERINGBAY, target_count=1, townhalls=3, requirements=[(UnitTypeId.BARRACKS, 3, False)]),
            BuildOrderStep(bot, self, 'techlab', UnitTypeId.BARRACKSTECHLAB, requirements=[(UnitTypeId.BARRACKS, 2, True)]),
            BuildOrderStep(bot, self, 'gas #2', UnitTypeId.REFINERY, target_count=2, workers=28),
            BuildOrderStep(bot, self, '+1 atk', UpgradeId.TERRANINFANTRYWEAPONSLEVEL1, requirements=[(UnitTypeId.ENGINEERINGBAY, 1, True)]),
            BuildOrderStep(bot, self, 'stim', UpgradeId.STIMPACK, requirements=[(UnitTypeId.BARRACKSTECHLAB, 1, True)]),
            BuildOrderStep(bot, self, 'techlab #2', UnitTypeId.BARRACKSTECHLAB, target_count=2, requirements=[(UnitTypeId.BARRACKS, 3, True)], upgrades_required=[UpgradeId.STIMPACK]),
            BuildOrderStep(bot, self, 'Rax 4/5', UnitTypeId.BARRACKS, target_count=5, townhalls=3, requirements=[(UnitTypeId.BARRACKSTECHLAB, 2, False)]),
            BuildOrderStep(bot, self, 'shield', UpgradeId.SHIELDWALL, requirements=[(UnitTypeId.BARRACKSTECHLAB, 2, True)]),
            BuildOrderStep(bot, self, 'gas #3', UnitTypeId.REFINERY, target_count=3, requirements=[(UnitTypeId.BARRACKS, 5, False)], workers=35),
            BuildOrderStep(bot, self, 'techlab #3', UnitTypeId.BARRACKSTECHLAB, target_count=3, requirements=[(UnitTypeId.BARRACKS, 4, True)]),
            BuildOrderStep(bot, self, 'concussive', UpgradeId.PUNISHERGRENADES, requirements=[(UnitTypeId.BARRACKSTECHLAB, 3, True)]),
            BuildOrderStep(bot, self, 'facto', UnitTypeId.FACTORY, upgrades_required=[UpgradeId.PUNISHERGRENADES]),
            BuildOrderStep(bot, self, '+1 def', UpgradeId.TERRANINFANTRYARMORSLEVEL1, upgrades_required=[UpgradeId.TERRANINFANTRYWEAPONSLEVEL1]),
            BuildOrderStep(bot, self, 'starport', UnitTypeId.STARPORT),
            BuildOrderStep(bot, self, 'Reactor #2 (from facto)', UnitTypeId.FACTORYREACTOR, target_count=2, requirements=[(UnitTypeId.STARPORT, 1, False)]),
        ]

        self.production_queues = [
            ProductionQueue(
                bot,
                UnitTypeId.BARRACKS,
                [(UnitTypeId.REAPER, 1), (UnitTypeId.MARINE, 2)],
            ),
        ]
        
        self.swap_plans = [
            AddonSwap(
                bot,
                UnitTypeId.FACTORY,
                UnitTypeId.STARPORT,
                UnitTypeId.REACTOR,
            )
        ]