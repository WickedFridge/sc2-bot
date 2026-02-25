from __future__ import annotations
from typing import List, TYPE_CHECKING
import random
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.builds.cc_first_two_rax import CCFirstTwoRax
from bot.strategy.build_order.builds.defensive_cyclone import DefensiveCyclone
from bot.strategy.build_order.builds.dummy_build import Dummybuild
from bot.strategy.build_order.builds.koka_build import KokaBuild
from bot.strategy.build_order.builds.two_rax_reaper_defensive import DefensiveTwoRax
from bot.strategy.build_order.builds.two_rax_reapers import TwoRaxReapers
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI

if TYPE_CHECKING:
    from bot.bot import WickedBot

build_order_manager: BuildOrderManager | None = None

class BuildOrderManager:
    bot: BotAI
    build: BuildOrder

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.build = KokaBuild(self.bot)

    @property
    def wicked(self) -> WickedBot:
        return self.bot  # type: ignore
    
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
                    # KokaBuild(self.bot),
                    # CCFirstTwoRax(self.bot)
                ])
            case Matchup.TvP:
                self.build = random.choice([
                    # DefensiveCyclone(self.bot),
                    # Dummybuild(self.bot),
                    KokaBuild(self.bot),
                    # CCFirstTwoRax(self.bot)
                ])
            case _:
                self.build = KokaBuild(self.bot)

        # Register any addon swaps declared by the selected build order.
        # If the build order has no addon_swaps attribute, an empty list is used
        # so any swaps from a previous build order are cleared.
        addon_swaps: list = getattr(self.build, "addon_swaps", [])
        self.wicked.addon_swap.register_swaps(addon_swaps)

def get_build_order(bot: BotAI) -> BuildOrderManager:
    global build_order_manager
    if (build_order_manager is None):
        build_order_manager = BuildOrderManager(bot)
    return build_order_manager