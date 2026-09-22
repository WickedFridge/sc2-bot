from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional
from bot.macro.expansion import Expansion
from bot.strategy.strategy_types import Situation
from bot.utils.army import Army
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.utils import closest_point, unscouted_points_around
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import burrowed_units, cloaked_units, tower_types, worker_types

if TYPE_CHECKING:
    from bot.superbot import Superbot  # only imported for type hints

scouting: Scouting | None = None

tech_unlocked: dict[UnitTypeId, List[UnitTypeId]] = {
    # zerg tech
    UnitTypeId.SPAWNINGPOOL: [UnitTypeId.ZERGLING, UnitTypeId.QUEEN],
    UnitTypeId.ROACHWARREN: [UnitTypeId.ROACH, UnitTypeId.RAVAGER],
    UnitTypeId.BANELINGNEST: [UnitTypeId.BANELING],
    UnitTypeId.LAIR: [UnitTypeId.OVERSEER, UnitTypeId.CHANGELING, UnitTypeId.CHANGELINGMARINE, UnitTypeId.CHANGELINGMARINESHIELD],
    UnitTypeId.HYDRALISKDEN: [UnitTypeId.HYDRALISK],
    UnitTypeId.INFESTATIONPIT: [UnitTypeId.INFESTOR, UnitTypeId.SWARMHOSTMP],
    UnitTypeId.SPIRE: [UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR],
    UnitTypeId.LURKERDEN: [UnitTypeId.LURKER],
    UnitTypeId.HIVE: [UnitTypeId.VIPER],
    UnitTypeId.ULTRALISKCAVERN: [UnitTypeId.ULTRALISK],
    UnitTypeId.GREATERSPIRE: [UnitTypeId.BROODLORD],

    # terran tech
    UnitTypeId.BARRACKS: [UnitTypeId.MARINE, UnitTypeId.REAPER],
    UnitTypeId.BARRACKSTECHLAB: [UnitTypeId.MARAUDER],
    UnitTypeId.GHOSTACADEMY: [UnitTypeId.GHOST],
    UnitTypeId.FACTORY: [UnitTypeId.HELLION, UnitTypeId.WIDOWMINE],
    UnitTypeId.FACTORYTECHLAB: [UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED],
    UnitTypeId.ARMORY: [UnitTypeId.HELLIONTANK, UnitTypeId.THOR, UnitTypeId.THORAP, UnitTypeId.WIDOWMINEBURROWED],
    UnitTypeId.STARPORT: [UnitTypeId.VIKING, UnitTypeId.MEDIVAC, UnitTypeId.LIBERATOR],
    UnitTypeId.STARPORTTECHLAB: [UnitTypeId.RAVEN, UnitTypeId.BANSHEE],
    UnitTypeId.FUSIONCORE: [UnitTypeId.BATTLECRUISER],

    # protoss tech
    UnitTypeId.GATEWAY: [UnitTypeId.ZEALOT],
    UnitTypeId.CYBERNETICSCORE: [UnitTypeId.STALKER, UnitTypeId.SENTRY, UnitTypeId.ADEPT],
    UnitTypeId.TEMPLARARCHIVE: [UnitTypeId.HIGHTEMPLAR, UnitTypeId.ARCHON],
    UnitTypeId.DARKSHRINE: [UnitTypeId.DARKTEMPLAR, UnitTypeId.ARCHON],
    UnitTypeId.STARGATE: [UnitTypeId.PHOENIX, UnitTypeId.ORACLE, UnitTypeId.VOIDRAY],
    UnitTypeId.FLEETBEACON: [UnitTypeId.TEMPEST, UnitTypeId.CARRIER, UnitTypeId.MOTHERSHIP],
    UnitTypeId.ROBOTICSFACILITY: [UnitTypeId.OBSERVER, UnitTypeId.IMMORTAL, UnitTypeId.WARPPRISM],
    UnitTypeId.ROBOTICSBAY: [UnitTypeId.COLOSSUS, UnitTypeId.DISRUPTOR]
}

class Scouting:
    bot: Superbot
    known_enemy_army: Army
    known_enemy_workers: Army
    known_enemy_buildings: Units
    known_enemy_tech: List[UnitTypeId] = []
    possible_enemy_composition: List[UnitTypeId] = []
    known_enemy_composition: List[UnitTypeId] = []
    known_enemy_upgrades: List[UpgradeId] = []
    situation: Situation = Situation.STABLE
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
        self.known_enemy_army = Army(Units([], bot), bot)
        self.known_enemy_workers = Army(Units([], bot), bot)
        self.known_enemy_buildings = Units([], bot)
        self.scout_tag = None
        self.engaged_worker_tag = None
        self.engaged_min_distance = 0
    
    @property
    def enemy_composition(self) -> dict[UnitTypeId, float]:
        enemy_composition: dict[UnitTypeId, float] = {}
        army_composition: dict[UnitTypeId, int] = self.known_enemy_army.composition
        total_units: float = self.known_enemy_army.units.amount
        for unit_type in army_composition:
            enemy_composition[unit_type] = army_composition[unit_type] / total_units
        return enemy_composition
    
    def detect_enemy_composition(self, unit_type: UnitTypeId):
        if (unit_type not in self.known_enemy_composition):
            self.known_enemy_composition.append(unit_type)
        if (unit_type not in self.possible_enemy_composition):
            self.possible_enemy_composition.append(unit_type)
            print(f"{unit_type} detected !")
            deduced_tech: List[UnitTypeId] = self.detect_deduced_tech(unit_type)
            for tech in deduced_tech:
                self.conclude_compo_from_tech(tech)
    
    def conclude_compo_from_tech(self, tech: UnitTypeId):
        unlocked: List[UnitTypeId] = tech_unlocked.get(tech, [])
        for unit_type in unlocked:
            if (unit_type not in self.possible_enemy_composition):
                self.possible_enemy_composition.append(unit_type)
                print(f"{unit_type} potentially detected !")
    
    def detect_enemy_army(self):
        main: Point2 = self.bot.expansions.main.position
        enemy_main: Point2 = self.bot.expansions.enemy_main.position
        enemy_units: Units = self.bot.enemy_units.filter(lambda unit: (
            unit.type_id not in tower_types
            and unit.type_id not in worker_types
        ))
        agressive_enemy_units: Units = enemy_units.filter(lambda unit: (
            unit.type_id not in [UnitTypeId.QUEEN, UnitTypeId.OVERLORD]
            or unit.distance_to_squared(main) < unit.distance_to_squared(enemy_main)
        ))

        self.known_enemy_army.detect_units(agressive_enemy_units)
        for enemy in enemy_units:
            self.detect_enemy_composition(enemy.type_id)

    def detect_enemy_workers(self):
        enemy_workers: Units = self.bot.enemy_units(worker_types)
        self.known_enemy_workers.detect_units(enemy_workers)
            
    def detect_enemy_buildings(self):
        enemy_buildings: Units = self.bot.enemy_structures
        for building in enemy_buildings:
            if (building.tag not in self.known_enemy_buildings.tags):
                self.known_enemy_buildings.append(building)
            if (building.type_id not in self.known_enemy_tech):
                self.known_enemy_tech.append(building.type_id)
                print(f"{building.type_id} detected !")
                unlocked: List[UnitTypeId] = tech_unlocked.get(building.type_id, [])
                for tech in unlocked:
                    if (tech not in self.possible_enemy_composition):
                        self.possible_enemy_composition.append(tech)
                        print(f"{tech} potentially detected !")

    def detect_deduced_tech(self, unit_type: UnitTypeId) -> List[UnitTypeId]:
        deduced_tech: List[UnitTypeId] = []
        for tech_building, units_unlocked in tech_unlocked.items():
            if (unit_type in units_unlocked and tech_building not in deduced_tech):
                deduced_tech.append(tech_building)
        return deduced_tech
    
    async def detect_enemy_upgrades(self):
        await self.detect_burrow()
        await self.detect_speeding()

    async def detect_burrow(self):
        if (UpgradeId.BURROW in self.known_enemy_upgrades):
            return
        offensive_units: Units = self.known_enemy_army.units.filter(lambda unit: unit.type_id != UnitTypeId.QUEEN)
        if (
            any([unit_type in burrowed_units + cloaked_units for unit_type in self.possible_enemy_composition])
            or self.bot.enemy_units.filter(lambda unit: unit.is_burrowed).amount >= 1
            or (
                self.known_enemy_army.units(UnitTypeId.ROACH).amount >= 5
                and self.known_enemy_army.units(UnitTypeId.ROACH).amount >= 0.7 * offensive_units.amount
            )
            or self.bot.time > 60 * 10
        ):
            print("Burrow/cloack detected !")
            await self.bot.client.chat_send("Tag:Detection", False)
            self.known_enemy_upgrades.append(UpgradeId.BURROW)

    async def detect_speeding(self):
        if (UpgradeId.ZERGLINGMOVEMENTSPEED in self.known_enemy_upgrades):
            return
        enemy_zerglings: Units = self.bot.enemy_units(UnitTypeId.ZERGLING)
        if (
            enemy_zerglings.amount >= 1
            and enemy_zerglings.first.real_speed >= 6.5
        ):
            print("Speedling detected !")
            await self.bot.client.chat_send("Tag:Speedling", False)
            self.known_enemy_upgrades.append(UpgradeId.ZERGLINGMOVEMENTSPEED)

    def unit_died(self, unit_tag: int):
        self.bot.ghost_units.remove_by_tag(unit_tag)
        if (unit_tag in self.known_enemy_army.units.tags):
            self.known_enemy_army.remove_by_tag(unit_tag)
            enemy_army: dict = self.known_enemy_army.recap
            print("remaining enemy units :", enemy_army)
        elif (unit_tag in self.known_enemy_workers.units.tags):
            self.known_enemy_workers.remove_by_tag(unit_tag)
            print(f"remaining enemy workers : {self.known_enemy_workers.units.amount}")
        elif (unit_tag in self.known_enemy_buildings.tags):
            destroyed_building: Unit = self.known_enemy_buildings.by_tag(unit_tag)
            self.known_enemy_buildings.remove(destroyed_building)

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
    
def get_scouting(bot: Superbot) -> Scouting:
    global scouting
    if (scouting is None):
        scouting = Scouting(bot)
    return scouting