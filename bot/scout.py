from typing import List, Optional
from bot.superbot import Superbot
from bot.utils.matchup import Matchup, get_matchup
from bot.utils.point2_functions.utils import closest_point
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

class Scout:
    bot: Superbot
    scout_tag: int | None

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.scout_tag = None

    @property
    def scout(self) -> Optional[Unit]:
        if (self.scout_tag is None):
            return None
        return self.bot.units.find_by_tag(self.scout_tag)

    async def b2_against_proxy(self):
        if (self.bot.matchup != Matchup.TvP):
            return
        if (self.bot.workers.gathering.amount == 0):
            print("no worker available to scout o7")
            return
        barracks_amount: int = self.bot.structures(UnitTypeId.BARRACKS).amount 
        if (
            barracks_amount == 1
            and self.bot.expansions.b2.is_taken == False
            and (
                self.bot.expansions.b2.is_scouted == False
                or self.bot.expansions.main.is_scouted == False
            )
        ):
            # if we don't already have a scout assigned, we assign one
            if (self.scout_tag is None):
                self.scout_tag = self.bot.workers.gathering.closest_to(self.bot.expansions.b2.position).tag
            if (self.scout is None):
                print("ERROR CAN'T FIND SCOUT !")
                return
            
            # scout b2 first, ten the interior of the main
            unscouted_b2: List[Point2] = self.bot.expansions.b2.unscouted_points
            unscouted_main: List[Point2] = self.bot.expansions.b2.unscouted_points
            target: Point2
            if (len(unscouted_b2) > 0):
                # tell our scout to walk to the closest unscouted tile
                target: Point2 = closest_point(self.scout, unscouted_b2)
            else:
                target: Point2 = closest_point(self.scout, unscouted_main)
            self.scout.move(target)
            print(f'[{self.bot.time.__round__(1)}] Scouting, {len(unscouted_b2) + len(unscouted_main)} unscouted points left')
        else:
            if (self.scout_tag):
                self.scout_tag = None