from __future__ import annotations

from typing import TYPE_CHECKING

from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.build_order_step import BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.conservative_rax_expand import ConservativeRaxExpand
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_double_cyclone_magfield import DefensiveDoubleCycloneMagfield
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_mistral_211 import DefensiveMistral211
from bot.strategy.strategy_types import Situation

if TYPE_CHECKING:
    from bot.superbot import Superbot


class MacroBuild(BuildOrder):
    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.default_defensive_response = DefensiveCycloneTank(self.bot)
        self.defensive_responses = {
            Situation.CHEESE_WORKER_RUSH: ConservativeRaxExpand(self.bot),
            Situation.CHEESE_ROACH_RUSH: DefensiveCycloneTank(self.bot),
            Situation.CHEESE_CANNON_RUSH: DefensiveCycloneTank(self.bot),
            Situation.CHEESE_BUNKER_RUSH: DefensiveCycloneTank(self.bot),
            Situation.CHEESE_LING_DRONE: ConservativeRaxExpand(self.bot),
            Situation.CHEESE_LING_FLOOD: DefensiveCycloneTank(self.bot),
            Situation.CHEESE_REAPER_RUSH: DefensiveMistral211(self.bot),
            Situation.CHEESE_SKYTOSS: DefensiveDoubleCycloneMagfield(self.bot),
        }