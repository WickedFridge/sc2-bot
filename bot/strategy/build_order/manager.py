from __future__ import annotations
from typing import List
import bot
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.koka_build import KokaBuild
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
        self.build = KokaBuild(bot)

    def select_build(self, matchup: Matchup):
        if (matchup == Matchup.TvT):
            self.build = TwoRaxReapers(self.bot)

    def sanity_check(self):
        completed: dict[UnitTypeId, int] = {}
        for step in self.build.completed_steps:
            unit_id: UnitTypeId = step.step_id
            if (unit_id not in build_order_structures):
                continue
            if (unit_id in completed.keys()):
                completed[unit_id] += 1
            else:
                completed[unit_id] = 1
            
            # add flying buildings and other CCs
            unit_ids: List[UnitTypeId] = [unit_id]
            if (unit_id == UnitTypeId.COMMANDCENTER):
                unit_ids.extend([
                    UnitTypeId.ORBITALCOMMAND,
                    UnitTypeId.COMMANDCENTERFLYING,
                    UnitTypeId.ORBITALCOMMANDFLYING,
                    UnitTypeId.PLANETARYFORTRESS,
                ])
            if (unit_id == UnitTypeId.BARRACKS):
                unit_ids.append(UnitTypeId.BARRACKSFLYING)
            if (unit_id == UnitTypeId.FACTORY):
                unit_ids.append(UnitTypeId.FACTORYFLYING)
            if (unit_id == UnitTypeId.STARPORT):
                unit_ids.append(UnitTypeId.STARPORTFLYING)
            if (unit_id == UnitTypeId.FACTORYREACTOR):
                unit_ids.extend([
                    UnitTypeId.REACTOR,
                    UnitTypeId.STARPORTREACTOR
                ])
            building_amount: int = self.bot.structures(unit_ids).amount + sum([self.bot.already_pending(id) for id in unit_ids])
            if (building_amount < completed[unit_id]):
                print(f'Error in build order detected, unchecking -- {unit_id}')
                step.checked = False


def get_build_order(bot: BotAI) -> BuildOrderManager:
    global build_order_manager
    if (build_order_manager is None):
        build_order_manager = BuildOrderManager(bot)
    return build_order_manager