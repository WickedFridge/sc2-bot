from __future__ import annotations
from typing import List
import random
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.builds.cc_first_two_rax import CCFirstTwoRax
from bot.strategy.build_order.builds.dummy_build import Dummybuild
from bot.strategy.build_order.builds.koka_build import KokaBuild
from bot.strategy.build_order.builds.two_rax_reaper_defensive import DefensiveTwoRax
from bot.strategy.build_order.builds.two_rax_reapers import TwoRaxReapers
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI

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
                    # Dummybuild(self.bot)
                    # TwoRaxReapers(self.bot),
                    DefensiveTwoRax(self.bot),
                ])
            case Matchup.TvZ:
                self.build = random.choice([
                    TwoRaxReapers(self.bot),
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

def get_build_order(bot: BotAI) -> BuildOrderManager:
    global build_order_manager
    if (build_order_manager is None):
        build_order_manager = BuildOrderManager(bot)
    return build_order_manager