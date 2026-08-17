from typing import List, Optional
from bot.macro.expansion import Expansion
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.utils import closest_point, unscouted_points_around
from bot.utils.unit_tags import worker_types
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

class Scout:
    bot: Superbot
    scout_tag: int | None
    engaged_worker_tag: int | None
    engaged_min_distance: float

    # radius around a scouted zone within which an enemy building or worker is considered suspicious
    PROXY_SEARCH_RADIUS: int = 25
    # radius scouted around a proxy building found, in case there's a second one nearby
    BUILDING_SEARCH_RADIUS: int = 5
    # give up the chase once the enemy worker has pulled away this much from our closest approach
    DISENGAGE_MARGIN: float = 2

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.scout_tag = None
        self.engaged_worker_tag = None
        self.engaged_min_distance = 0

    @property
    def scout(self) -> Optional[Unit]:
        if (self.scout_tag is None):
            return None
        return self.bot.units.find_by_tag(self.scout_tag)

    # zones scouted for a proxy, in priority order: our next expansions first, the interior of the main last
    @property
    def _proxy_zones(self) -> List[Expansion]:
        zones: List[Expansion] = [
            self.bot.expansions.b2,
            self.bot.expansions.b3,
            self.bot.expansions.b4,
        ]

        if (self.bot.matchup == Matchup.TvP):
            zones.append(self.bot.expansions.main)
        return zones

    def _proxy_building_points(self, zones: List[Expansion]) -> List[Point2]:
        # for every enemy building found near a scouted zone, scout a bit around it: there may be a second one
        nearby_enemy_structures: Units = self.bot.enemy_structures.filter(
            lambda structure: any(structure.distance_to(zone.position) < self.PROXY_SEARCH_RADIUS for zone in zones)
        )
        points: List[Point2] = []
        for structure in nearby_enemy_structures:
            for point in unscouted_points_around(self.bot, structure.position, self.BUILDING_SEARCH_RADIUS):
                if (point not in points):
                    points.append(point)
        return points

    def _engage_enemy_worker(self, scout: Unit, zones: List[Expansion]) -> bool:
        """ Attacks a nearby enemy worker, giving up the chase once it pulls away. Returns True if the scout was given an attack order this frame. """
        if (self.engaged_worker_tag is not None):
            engaged_worker: Optional[Unit] = self.bot.enemy_units.find_by_tag(self.engaged_worker_tag)
            if (engaged_worker is not None):
                distance: float = scout.distance_to(engaged_worker)
                self.engaged_min_distance = min(self.engaged_min_distance, distance)
                if (distance <= self.engaged_min_distance + self.DISENGAGE_MARGIN):
                    scout.attack(engaged_worker)
                    return True
            # dead, out of vision, or pulling away: give up and resume scouting
            self.engaged_worker_tag = None

        nearby_enemy_workers: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.type_id in worker_types
                and any(unit.distance_to(zone.position) < self.PROXY_SEARCH_RADIUS for zone in zones)
            )
        )
        if (nearby_enemy_workers.amount == 0):
            return False

        target: Unit = nearby_enemy_workers.closest_to(scout)
        self.engaged_worker_tag = target.tag
        self.engaged_min_distance = scout.distance_to(target)
        scout.attack(target)
        return True

    async def scout_proxy(self):
        scout_needed_situations: List[Situation] = [
            Situation.STABLE,
            Situation.PROXY_BUILDINGS,
            Situation.CHEESE_BUNKER_RUSH,
            Situation.CHEESE_CANNON_RUSH,
            Situation.CHEESE_UNKNOWN,
            Situation.CHEESE_PROXY_RAX,
        ]
        if (self.bot.matchup not in [Matchup.TvP, Matchup.TvT] or self.bot.scouting.situation not in scout_needed_situations):
            return
        if (self.bot.workers.gathering.amount == 0):
            print("no worker available to scout o7")
            return
        barracks_amount: int = self.bot.structures(UnitTypeId.BARRACKS).amount
        rax_60: int = self.bot.structures(UnitTypeId.BARRACKS).filter(lambda rax: rax.build_progress >= 0.60).amount
        matchup_condition: bool = (
            (self.bot.matchup == Matchup.TvP and barracks_amount == 1)
            or (self.bot.matchup == Matchup.TvT and rax_60 >= 1)
        )

        zones: List[Expansion] = self._proxy_zones
        extra_scout_points: List[Point2] = self._proxy_building_points(zones)

        if (
            not matchup_condition
            or self.bot.expansions.b2.is_ready
            or (
                all(zone.is_fully_scouted for zone in zones)
                and len(extra_scout_points) == 0
            )
        ):
            self.scout_tag = None
            self.engaged_worker_tag = None
            return

        # if we don't already have a scout assigned, we assign one
        if (self.scout_tag is None):
            self.scout_tag = self.bot.workers.gathering.closest_to(self.bot.expansions.b2.position).tag
        if (self.scout is None):
            print("ERROR CAN'T FIND SCOUT !")
            return
        scout: Unit = self.scout

        if (self._engage_enemy_worker(scout, zones)):
            return

        # scout each zone in priority order, then around any proxy building found
        pools: List[List[Point2]] = [zone.unscouted_points for zone in zones] + [extra_scout_points]
        remaining: int = sum(len(pool) for pool in pools)
        target_pool: List[Point2] = next(pool for pool in pools if len(pool) > 0)
        target: Point2 = closest_point(scout.position, target_pool)

        scout.move(target)
        print(f'[{self.bot.time.__round__(1)}] Scouting, {remaining} unscouted points left')