from bot.macro.expansion_manager import Expansions
from bot.macro.map import MapData
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI


class Superbot(BotAI):
    @property
    def matchup(self) -> Matchup:
        pass
    
    @property
    def expansions(self) -> Expansions:
        pass
    
    @property
    def map(self) -> MapData:
        pass