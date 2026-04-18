from __future__ import annotations
from typing import List, TYPE_CHECKING
import random
from bot.strategy.build_order.addon_swap import SwapState
from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_mistral_211 import DefensiveMistral211
from bot.strategy.build_order.builds.macro_builds.cc_first_two_rax import CCFirstTwoRax
from bot.strategy.build_order.builds.macro_builds.cyclone_3_raven import Cyclone3Raven
from bot.strategy.build_order.builds.unused.defensive_cyclone import DefensiveCyclone
from bot.strategy.build_order.builds.macro_builds.macro_cyclone import MacroCyclone
from bot.strategy.build_order.builds.unused.dummy_build import Dummybuild
from bot.strategy.build_order.builds.macro_builds.koka_build import KokaBuild
from bot.strategy.build_order.builds.macro_builds.reactor_hellion_3cc_1_1 import Greedy22Timing
from bot.strategy.build_order.builds.unused.two_rax_reaper_defensive import DefensiveTwoRax
from bot.strategy.build_order.builds.macro_builds.two_rax_reapers import TwoRaxReapers
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
        # self.build = DefensiveMistral211(self.bot)
        # return
    
        match(matchup):
            case Matchup.TvT:
                self.build = random.choice([
                    # Dummybuild(self.bot)
                    # TwoRaxReapers(self.bot),
                    # MacroCyclone(self.bot),
                    Cyclone3Raven(self.bot),
                    # DefensiveTwoRax(self.bot),
                ])
            case Matchup.TvZ:
                self.build = random.choice([
                    # TwoRaxReapers(self.bot),
                    Greedy22Timing(self.bot),
                    # DefensiveCyclone(self.bot),
                    # KokaBuild(self.bot),
                    # CCFirstTwoRax(self.bot)
                ])
            case Matchup.TvP:
                self.build = random.choice([
                    MacroCyclone(self.bot),
                    # Dummybuild(self.bot),
                    # KokaBuild(self.bot),
                    # CCFirstTwoRax(self.bot)
                ])
            case _:
                self.build = KokaBuild(self.bot)

    def switch_build(self, new_build_order: BuildOrder) -> None:
    # Abort any in-progress swaps from the old build order
        for plan in self.build.swap_plans:
            if (not plan.is_finished and plan.state != SwapState.PENDING):
                print(f"[BuildOrder] Aborting in-progress swap {plan.name} due to BO switch.")
                plan.state = SwapState.ABORTED

        self.build = new_build_order
        self.build.reconcile()

def get_build_order(bot: BotAI) -> BuildOrderManager:
    global build_order_manager
    if (build_order_manager is None):
        build_order_manager = BuildOrderManager(bot)
    return build_order_manager