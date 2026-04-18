from bot.strategy.build_order.build_order import BuildOrder
from bot.strategy.build_order.build_order_step import BuildOrderStep
from bot.strategy.build_order.builds.defensive_reaction_builds.conservative_rax_expand import ConservativeRaxExpand
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_cyclone_tank import DefensiveCycloneTank
from bot.strategy.build_order.builds.defensive_reaction_builds.defensive_mistral_211 import DefensiveMistral211
from bot.strategy.strategy_types import Situation
from sc2.bot_ai import BotAI


class MacroBuild(BuildOrder):
    def __init__(self, bot: BotAI):
        super().__init__(bot)
        self.default_defensive_response = ConservativeRaxExpand(bot)
        self.defensive_responses = {
            Situation.CHEESE_ROACH_RUSH: DefensiveCycloneTank(self.bot),
            Situation.CHEESE_BUNKER_RUSH: DefensiveCycloneTank(self.bot),
            Situation.CHEESE_LING_FLOOD: DefensiveMistral211(self.bot), 
        }