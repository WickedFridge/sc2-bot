from bot.macro.expansion_manager import Expansions
from bot.macro.map import MapData
from bot.scouting.scouting import Scouting
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId


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

    @property
    def scouting(self) -> Scouting:
        pass

    @property
    def orbital_tech_available(self) -> bool:
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9