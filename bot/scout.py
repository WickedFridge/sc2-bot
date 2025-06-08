from typing import List, Optional
from bot.macro.expansion_manager import Expansions
from bot.utils.matchup import Matchup, get_matchup
from bot.utils.point2_functions import closest_point
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

class Scout:
    bot: BotAI
    scout_tag: int | None

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.scout_tag = None

    @property
    def matchup(self) -> Matchup:
        return get_matchup(self.bot)

    @property
    def scout(self) -> Optional[Unit]:
        if (self.scout_tag is None):
            return None
        return self.bot.units.find_by_tag(self.scout_tag)

    async def b2_against_proxy(self):
        if (self.matchup != Matchup.TvP):
            return
        if (self.bot.workers.gathering.amount == 0):
            print("no worker available to scout o7")
            return
        barracks_amount: int = self.bot.structures(UnitTypeId.BARRACKS).amount 
        if (
            barracks_amount == 1
            and self.bot.expansions.b2.is_taken == False
            and self.bot.expansions.b2.is_scouted == False
        ):
            # if we don't already have a scout assigned, we assign one
            if (self.scout_tag is None):
                self.scout_tag = self.bot.workers.gathering.closest_to(self.bot.expansions.b2.position).tag
            if (self.scout is None):
                print("ERROR CAN'T FIND SCOUT !")
                return
            # if our scout is closest to the main than the b2, just tell them to go to the b2
            distance_to_main: float = self.scout.distance_to(self.bot.expansions.main.position)
            distance_to_b2: float = self.scout.distance_to(self.bot.expansions.b2.position)
            if (distance_to_b2 > distance_to_main):
                self.scout.move(self.bot.expansions.b2.position)
                return
            
            # tell our scout to walk to the closest unscouted tile
            unscouted_points: List[Point2] = self.bot.expansions.b2.unscouted_points
            target: Point2 = closest_point(self.scout, unscouted_points)
            self.scout.move(target)
            print(f'[{self.bot.time.__round__(1)}] Scouting, {unscouted_points.__len__()} unscouted points left')
        else:
            if (self.scout_tag):
                self.scout_tag = None