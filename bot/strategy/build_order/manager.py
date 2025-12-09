from __future__ import annotations
from typing import List
import random
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.cc_first_two_rax import CCFirstTwoRax
from bot.strategy.build_order.dummy_build import Dummybuild
from bot.strategy.build_order.koka_build import KokaBuild
from bot.strategy.build_order.two_rax_reaper_defensive import DefensiveTwoRax
from bot.strategy.build_order.two_rax_reapers import TwoRaxReapers
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from bot.utils.unit_tags import build_order_structures

build_order_manager: BuildOrderManager | None = None

class BuildOrderManager:
    bot: BotAI
    build: BuildOrder

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.build = KokaBuild(self.bot)

    def select_build(self, matchup: Matchup):
        # self.build = Dummybuild(self.bot)
        match(matchup):
            case Matchup.TvT:
                self.build = random.choice([
                    # TwoRaxReapers(self.bot),
                    DefensiveTwoRax(self.bot),
                ])
            case Matchup.TvZ:
                self.build = random.choice([
                    # TwoRaxReapers(self.bot),
                    KokaBuild(self.bot),
                    # CCFirstTwoRax(self.bot)
                ])
            case Matchup.TvP:
                self.build = random.choice([
                    KokaBuild(self.bot),
                    CCFirstTwoRax(self.bot)
                ])
            case _:
                self.build = KokaBuild(self.bot)
    
    def sanity_check(self):
        completed: dict[UnitTypeId, int] = {}
        for step in self.build.steps:
            unit_id: UnitTypeId = step.step_id
            if (unit_id not in build_order_structures):
                continue
            should_check: bool = step.checked
            if (unit_id in completed.keys()):
                completed[unit_id] += 1
            else:
                completed[unit_id] = 1
            
            # add flying buildings
            unit_ids: List[UnitTypeId] = [unit_id]
            if (unit_id == UnitTypeId.SUPPLYDEPOT):
                unit_ids.append(UnitTypeId.SUPPLYDEPOTLOWERED)
            if (unit_id == UnitTypeId.BARRACKS):
                unit_ids.append(UnitTypeId.BARRACKSFLYING)
            if (unit_id == UnitTypeId.FACTORY):
                unit_ids.append(UnitTypeId.FACTORYFLYING)
            if (unit_id == UnitTypeId.STARPORT):
                unit_ids.append(UnitTypeId.STARPORTFLYING)
            if (unit_id == UnitTypeId.FACTORYREACTOR):
                unit_ids.append(UnitTypeId.STARPORTREACTOR)
            
            building_amount: int = self.bot.structures(unit_ids).ready.amount + sum([self.bot.already_pending(id) for id in unit_ids])
            # specific case of CommandCenter since we start with one
            if (unit_id == UnitTypeId.COMMANDCENTER):
                building_amount = self.bot.townhalls.ready.amount + self.bot.already_pending(unit_id) - 1
            
            should_check = building_amount >= completed[unit_id]
            if (should_check != step.checked):
                step.checked = should_check
                print(f'buildings {unit_ids}: {building_amount}/{completed[unit_id]}')
                step.print_check()
                

def get_build_order(bot: BotAI) -> BuildOrderManager:
    global build_order_manager
    if (build_order_manager is None):
        build_order_manager = BuildOrderManager(bot)
    return build_order_manager