from __future__ import annotations
import bot
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.koka_build import KokaBuild
from bot.strategy.build_order.two_rax_reapers import TwoRaxReapers
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI

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


def get_build_order(bot: BotAI) -> BuildOrderManager:
    global build_order_manager
    if (build_order_manager is None):
        build_order_manager = BuildOrderManager(bot)
    return build_order_manager