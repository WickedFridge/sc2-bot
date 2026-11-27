from collections import deque
import math
from typing import List, Optional

from bot.macro.map.influence_maps.layers.buildings_layer import BUNKER_RADIUS
from bot.macro.map.map import MapData, get_map
from bot.scouting.ghost_units.ghost_units import GhostUnit, GhostUnits
from bot.utils.army import Army
from bot.utils.unit_supply import weighted_units_supply
from bot.utils.matchup import Matchup, get_matchup
from bot.utils.point2_functions.ramps import find_closest_bottom_ramp
from bot.utils.point2_functions.utils import center, closest_point, position_behind_worker_line, same_height_points_around
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing, valid_building_position
from bot.utils.unit_functions import worker_amount_mineral_field, worker_amount_vespene_geyser
from sc2.bot_ai import BotAI
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.game_info import Ramp
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import townhalls, menacing, worker_types
from functools import cached_property

# mining bunker touching a side of the townhall on that many tiles (1 = measured as the best layout, 3 max)
BUNKER_MINING_CONTACT_TILES: int = 1

class Expansion(CachedClass):
    position: Point2
    distance_from_main: float
    mineral_line: Point2
    # Both geysers are on the same side of the mineral line
    can_bunker_mine: bool
    # Computed once by the buildings layer at initialization (None if the base can't bunker mine)
    bunker_mining_position: Optional[Point2] = None
    radius: int = 12
    # half of the townhall's 5x5 footprint
    FOOTPRINT_RADIUS: float = 2.5
    # A base with a bunker is defended once it has this many defenders (bunker passengers + units around)
    MIN_DEFENDERS: int = 4
    # Our units closer than this to the base (or to its defensive structure) defend it
    GARRISON_RADIUS: float = 12
    STRUCTURE_GARRISON_RADIUS: float = 6
    # Units closer than this to the base are considered on site
    PRESENCE_RADIUS: float = 15
    last_scouted: float = 0
    _potentially_enemy: bool = False
    _unscouted_candidates: Optional[List[Point2]] = None

    def __init__(self, bot: BotAI, position: Point2, distance: float) -> None:
        super().__init__(bot)
        self.position = position
        self.distance_from_main = distance
        # The resources layout is static: compute it once at game start, while every resource is still there
        minerals: Units = self.bot.mineral_field.closer_than(10, position)
        geysers: Units = self.bot.vespene_geyser.closer_than(10, position)
        self.mineral_line = self._compute_mineral_line(minerals, geysers)
        self.can_bunker_mine = self._compute_can_bunker_mine(minerals, geysers)

    def _compute_mineral_line(self, minerals: Units, geysers: Units) -> Point2:
        resources: Units = minerals + geysers
        if (resources.amount == 0):
            return self.position.towards(self.bot.game_info.map_center, 5)
        return resources.center

    def _compute_can_bunker_mine(self, minerals: Units, geysers: Units) -> bool:
        """
        Both geysers are on the same side of the mineral line, i.e. no mineral field
        lies between them when sorted by angle around the townhall.
        """
        if (geysers.amount != 2 or minerals.amount == 0):
            return False
        reference_offset: Point2 = minerals.center - self.position
        reference_angle: float = math.atan2(reference_offset.y, reference_offset.x)

        def relative_angle(resource: Unit) -> float:
            # angle from the mineral line's direction, normalized in [-pi, pi)
            offset: Point2 = resource.position - self.position
            angle: float = math.atan2(offset.y, offset.x) - reference_angle
            return (angle + math.pi) % (2 * math.pi) - math.pi

        low, high = sorted(relative_angle(geyser) for geyser in geysers)
        return not any(low < relative_angle(mineral) < high for mineral in minerals)

    @cached_property
    def is_main(self) -> bool:
        return self.position == self.bot.start_location
    
    @custom_cache_once_per_frame
    def is_taken(self) -> bool:
        townhalls: Units = self.bot.townhalls
        if (townhalls.amount == 0):
            return False
        for th in townhalls.not_flying:
            if (th.position == self.position):
                return True
        return self.has_incoming_townhall

    @custom_cache_once_per_frame
    def has_incoming_townhall(self) -> bool:
        """One of our townhalls is flying to the slot (which may not have been scouted yet)."""
        return any(townhall.order_target == self.position for townhall in self.bot.townhalls.flying)

    @custom_cache_once_per_frame
    def is_unknown(self) -> bool:
        return self.bot.state.visibility[self.position.rounded] == 0

    @custom_cache_once_per_frame
    def has_enemy_buildings_around(self) -> bool:
        if (self.bot.enemy_structures.amount == 0):
            return False
        return self.bot.enemy_structures.filter(
            lambda building: (
                building.distance_to(self.position) < self.radius + 5
                and self.bot.get_terrain_height(building.position) == self.bot.get_terrain_height(self.position)
            )
        ).amount > 0

    @custom_cache_once_per_frame
    def is_scouted(self) -> bool:
        return self.bot.state.visibility[self.position.rounded] >= 1
    
    @custom_cache_once_per_frame
    def is_visible(self) -> bool:
        return self.bot.state.visibility[self.position.rounded] == 2
    
    @custom_cache_once_per_frame
    def is_populated(self) -> bool:
        return self.bot.structures.closest_distance_to(self.position) <= 5
    
    @custom_cache_once_per_frame
    def is_enemy(self) -> bool:
        # if is enemy main unscouted, return True
        if (self.position == self.bot.enemy_start_locations[0] and self.is_unknown):
            return True

        enemy_townhalls: Units = self.bot.enemy_structures.filter(lambda unit : unit.type_id in townhalls)
        return enemy_townhalls.amount > 0 and enemy_townhalls.closest_distance_to(self.position) <= 0.5
    
    @custom_cache_once_per_frame
    def is_ready(self) -> bool:
        return self.is_taken and self.cc.is_ready and not self.cc.is_flying

    @custom_cache_once_per_frame
    def is_probably_free(self) -> bool:
        return (
            (self.is_free or self.is_unknown)
            and not self.has_incoming_townhall
            and not self.is_potentially_enemy
            and self.no_enemy_around
        )

    @custom_cache_once_per_frame
    def is_landable(self) -> bool:
        """
        Nothing known prevents a townhall from landing on the slot.
        Unlike is_free, an incoming townhall doesn't make it unavailable.
        """
        if (any(townhall.position == self.position for townhall in self.bot.townhalls.not_flying) or self.is_enemy):
            return False
        if (self.is_unknown):
            return True
        return (
            self.mineral_fields.amount >= 1
            and self.is_buildable
            and not self.is_blocked_by_enemy
        )

    def is_on_footprint(self, unit: Unit | GhostUnit) -> bool:
        return (
            max(abs(unit.position.x - self.position.x), abs(unit.position.y - self.position.y))
            < self.FOOTPRINT_RADIUS + unit.radius
        )

    @custom_cache_once_per_frame
    def is_blocked_by_enemy(self) -> bool:
        """An enemy ground unit is on the footprint, either visible or assumed to be there (burrowed lurker...)."""
        # assumed_enemy_units doesn't include the visible units
        return (
            self.bot.enemy_units.not_flying.filter(self.is_on_footprint).amount >= 1
            or self.bot.ghost_units.assumed_enemy_units.not_flying.filter(self.is_on_footprint).amount >= 1
        )

    @custom_cache_once_per_frame
    def is_free(self) -> bool:
        return (
            self.is_scouted
            and not self.is_taken
            and not self.is_enemy
            and self.mineral_fields.amount >= 1
            and self.is_buildable
        )
    
    @custom_cache_once_per_frame
    def is_buildable(self) -> bool:
        """A CC can land on the slot (no creep, rocks/debris or building on the footprint)."""
        return self.bot.map.influence_maps.buildings.should_build_building(self.position, UnitTypeId.COMMANDCENTER, 2.5)

    @custom_cache_once_per_frame
    def is_safe(self) -> bool:
        # Positions with high HP PF are considered safe
        if (self.cc and self.cc.type_id == UnitTypeId.PLANETARYFORTRESS and self.cc.health_percentage >= 0.6):
            return True

        local_enemy_units: Units = self.bot.enemy_units.closer_than(8, self.position).filter(
            lambda unit: unit.can_attack_ground or unit.type_id in menacing
        )
        local_enemy_ground_units: Units = local_enemy_units.filter(lambda unit: not unit.is_flying)
        local_enemy_air_units: Units = local_enemy_units.filter(lambda unit: unit.is_flying)
        
        local_units: Units = self.bot.units.closer_than(8, self.position).filter(
            lambda unit: (
                unit.type_id not in worker_types
                and (unit.can_attack or unit.type_id in menacing)
            )
        )
        local_anti_ground_units: Units = local_units.filter(lambda unit: unit.can_attack_ground)
        local_anti_air_units: Units = local_units.filter(lambda unit: unit.can_attack_air)

        if (self.defending_structure and self.defending_structure.cargo_used >= 1):
            local_anti_ground_units.append(self.defending_structure)
        
        # strictly stronger when enemies are around, but no enemy at all means safe
        return (
            (
                local_enemy_ground_units.amount == 0
                or Army(local_anti_ground_units, self.bot).weighted_supply > Army(local_enemy_ground_units, self.bot).weighted_supply
            )
            and (
                local_enemy_air_units.amount == 0
                or Army(local_anti_air_units, self.bot).weighted_supply > Army(local_enemy_air_units, self.bot).weighted_supply
            )
        )
    
    @custom_cache_once_per_frame
    def no_enemy_around(self) -> bool:
        local_enemy_units: Units = self.bot.enemy_units.closer_than(8, self.mineral_line).filter(
            lambda unit: unit.can_attack_ground or unit.type_id in menacing
        )
        return local_enemy_units.amount == 0
    
    @custom_cache_once_per_frame
    def cc(self) -> Optional[Unit]:
        if (not self.is_taken):
            return None
        townhalls: Units = self.bot.townhalls
        for townhall in townhalls.sorted_by_distance_to(self.position):
            if (self.position in [townhall.position, townhall.order_target]):
                return townhall
        return None
    
    @custom_cache_once_per_frame
    def mineral_fields(self) -> Units:
        return self.bot.mineral_field.closer_than(10, self.position)
    
    @custom_cache_once_per_frame
    def refineries(self) -> Units:
        return self.bot.structures(UnitTypeId.REFINERY).ready.closer_than(10, self.position).filter(
            lambda refinery: self.bot.vespene_geyser.filter(
                lambda unit: unit.position == refinery.position and unit.has_vespene
            ).amount == 1
        )
    
    @custom_cache_once_per_frame
    def vespene_geysers(self) -> Units:
        return self.bot.vespene_geyser.closer_than(10, self.position)
    
    @custom_cache_once_per_frame
    def vespene_geysers_refinery(self) -> Units:
        return self.bot.vespene_geyser.filter(
            lambda geyser: geyser.has_vespene and self.bot.structures(UnitTypeId.REFINERY).ready.closer_than(10, self.position).filter(
                lambda refinery: refinery.position == geyser.position
            ).amount == 1
        )
    
    @custom_cache_once_per_frame
    def minerals(self) -> int:
        minerals: int = 0
        for mf in self.mineral_fields:
            minerals += mf.mineral_contents
        return minerals
    
    @custom_cache_once_per_frame
    def vespene(self) -> int:
        vespene: int = 0
        for vg in self.vespene_geysers_refinery:
            vespene += vg.vespene_contents
        return vespene

    @custom_cache_once_per_frame
    def is_depleted(self) -> bool:
        # cheap checks first: most bases still have (snapshot) minerals, so we rarely need the scouting check
        return (
            self.mineral_fields.amount == 0
            and self.vespene == 0
            and self.is_fully_scouted
        )
    
    @custom_cache_once_per_frame
    def mineral_workers(self) -> Units:
        if (self.mineral_fields.amount == 0):
            return Units([], self.bot)
        # build the tag set once instead of once per worker
        mineral_field_tags: set[int] = self.mineral_fields.tags
        return self.bot.workers.filter(
            lambda worker: (
                (
                    worker.is_gathering
                    and worker.order_target in mineral_field_tags
                ) or (
                    worker.is_returning
                    and worker.is_carrying_minerals
                    and worker.distance_to(self.position) <= 8
                ) or (
                    worker.is_moving
                    and isinstance(worker.order_target, Point2)
                    and worker.order_target.distance_to(self.mineral_line) <= 5
                )
            )
        )
    
    @custom_cache_once_per_frame
    def vespene_workers(self) -> Units:
        refinery_tags: set[int] = self.refineries.tags
        return self.bot.workers.closer_than(10, self.position).filter(
            lambda worker: (
                worker.is_carrying_vespene
                or worker.order_target in refinery_tags
            )
        )

    @custom_cache_once_per_frame
    def mineral_worker_count(self) -> int:
        return self.mineral_workers.amount

    @custom_cache_once_per_frame
    def vespene_worker_count(self) -> int:
        # bunker mined refineries are counted by BunkerMining (loaded workers aren't in assigned_harvesters)
        return sum(self.bot.bunker_mining.harvesters(refinery) for refinery in self.refineries)
    
    @custom_cache_once_per_frame
    def optimal_mineral_workers(self) -> float:
        if self.mineral_fields.amount == 0:
            return 0
        return sum(worker_amount_mineral_field(mf.mineral_contents) for mf in self.mineral_fields)

    @custom_cache_once_per_frame
    def optimal_vespene_workers(self) -> float:
        if self.refineries.amount == 0:
            return 0
        # 2 workers per refinery when bunker mined, 3 otherwise
        return sum(
            min(self.bot.bunker_mining.ideal_harvesters(refinery), worker_amount_vespene_geyser(refinery.vespene_contents))
            for refinery in self.refineries
        )

    @custom_cache_once_per_frame
    def mineral_saturation(self) -> float:
        if (self.optimal_mineral_workers == 0):
            return -1
        return self.mineral_worker_count / self.optimal_mineral_workers

    @custom_cache_once_per_frame
    def vespene_saturation(self) -> float:
        if (self.optimal_vespene_workers == 0):
            return -1
        return self.vespene_worker_count / self.optimal_vespene_workers

    @custom_cache_once_per_frame
    def desired_vespene_saturation(self) -> float:
        """
        Returns desired gas saturation between 0 and 1 based on mineral saturation:
        - 0 when mineral saturation <= 0.5
        - 1 when mineral saturation >= 0.75
        - Linear in-between
        """
        ms: float = self.mineral_saturation

        if (ms <= 0.5):
            return 0
        if (ms >= 0.75):
            return 1
        # Linear interpolation
        saturation: float = (ms - 0.5) / 0.25
        saturation = min(1.0, max(0.0, saturation))

        # Deprioritize gas if floating too much
        if self.bot.vespene >= 200 and self.bot.minerals <= 800:
            saturation *= 0.5  # or 0 if you want hard stop

        return saturation
    
    @custom_cache_once_per_frame
    def has_defensive_structure(self) -> bool:
        defenses: Units = self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).ready
        if (defenses.amount == 0):
            return False
        return (defenses.closest_distance_to(self.position) <= 12)

    @custom_cache_once_per_frame
    def is_defended(self) -> bool:
        """Has a PF, or enough defenders (bunker passengers + units around)"""
        return self.is_defended_without(None)

    def is_defended_without(self, unit: Optional[Unit]) -> bool:
        """Same as is_defended, without counting the given unit (so a defender doesn't leave a base that needs it)"""
        structure: Optional[Unit] = self.defending_structure
        if (structure is not None and structure.type_id == UnitTypeId.PLANETARYFORTRESS):
            return True
        passengers: int = len(structure.passengers) if structure is not None else 0
        defenders: Units = self.defenders if unit is None else self.defenders.tags_not_in({unit.tag})
        return defenders.amount + passengers >= self.MIN_DEFENDERS

    @custom_cache_once_per_frame
    def needs_defense(self) -> bool:
        """
        Bases to garrison: the ones with a defensive structure (a pending bunker counts: its builder
        needs protection and it will be filled as soon as it's done), or with a detected burrowed unit to clean
        """
        return self.has_defensive_structure or self.has_pending_bunker or self.has_burrowed_enemy

    @custom_cache_once_per_frame
    def has_pending_bunker(self) -> bool:
        """A bunker is in construction, or a worker is on its way to build one"""
        positions: List[Point2] = [bunker.position for bunker in self.bot.structures(UnitTypeId.BUNKER).not_ready]
        for worker in self.bot.workers:
            for order in worker.orders:
                if (order.ability.id == AbilityId.TERRANBUILD_BUNKER and isinstance(order.target, Point2)):
                    positions.append(order.target)
        return any(position.distance_to(self.position) <= 12 for position in positions)

    @custom_cache_once_per_frame
    def has_burrowed_enemy(self) -> bool:
        """A detected burrowed enemy is around (typically a zergling preventing the CC from landing)"""
        return self.bot.enemy_units.closer_than(self.GARRISON_RADIUS, self.position).filter(
            lambda unit: unit.is_burrowed and unit.can_be_attacked
        ).amount >= 1

    @custom_cache_once_per_frame
    def defenders(self) -> Units:
        """Our fighting units around the base or its defensive structure (bunker passengers aren't included)"""
        structure: Optional[Unit] = self.defending_structure
        return self.bot.units.filter(
            lambda unit: (
                unit.type_id not in worker_types
                and unit.type_id != UnitTypeId.MEDIVAC
                and (unit.can_attack or unit.type_id in menacing)
                and (
                    unit.distance_to(self.position) <= self.GARRISON_RADIUS
                    or (structure is not None and unit.distance_to(structure) <= self.STRUCTURE_GARRISON_RADIUS)
                )
            )
        )

    @custom_cache_once_per_frame
    def local_units(self) -> Units:
        """All our units around the base"""
        return self.bot.units.closer_than(self.PRESENCE_RADIUS, self.position)

    @custom_cache_once_per_frame
    def local_enemy_supply(self) -> float:
        """
        Weighted supply of the enemies able to fight around the base, last known positions included.
        Units that can't hurt anything (burrowed zergling, overlord...) don't count.
        """
        def is_fighting(unit: Unit | GhostUnit) -> bool:
            return unit.can_attack or unit.type_id in menacing
        local_enemies: Units = self.bot.enemy_units.closer_than(self.PRESENCE_RADIUS, self.position).filter(is_fighting)
        local_enemy_ghosts: GhostUnits = self.bot.ghost_units.assumed_enemy_units.closer_than(self.PRESENCE_RADIUS, self.position).filter(is_fighting)
        return weighted_units_supply(local_enemies) + weighted_units_supply(local_enemy_ghosts)
    
    @custom_cache_once_per_frame
    def detects(self) -> bool:
        turrets: Units = self.bot.structures(UnitTypeId.MISSILETURRET).ready
        if (turrets.amount == 0):
            return False
        return (turrets.closest_distance_to(self.position) <= 12)
    
    @custom_cache_once_per_frame
    def retreat_position(self) -> Point2:
        if (self.is_main):
            return self.bot.main_base_ramp.barracks_correct_placement
        if (self.has_defensive_structure and self.mineral_fields.amount >= 1):
            close_bunkers: Units = self.bot.structures(UnitTypeId.BUNKER).ready.closer_than(12, self.position)
            if (close_bunkers.amount > 1):
                return close_bunkers.center.towards(self.position, 0.5)
            if (close_bunkers.amount == 1):
                return center([self.position, close_bunkers.center])
            return center([self.position.towards(self.bot.game_info.map_center), self.mineral_line.towards(self.bot.game_info.map_center)])
        position: Point2 = self.bunker_ramp or self.bunker_forward
        return center([position, self.mineral_line])
    
    @custom_cache_once_per_frame
    def bunker_forward_in_pathing(self) -> Point2 | None:
        """Finds the nearest buildable position for a bunker, avoiding the Command Center's hitbox."""
        # Guard: CC reservation must exist before we search
        buildings_layer = self.bot.map.influence_maps.buildings
        cc_center: Point2 = self.position
        if (not self.is_main and self.cc is None and not buildings_layer.is_cc_reserved(cc_center)):
            print("CC reservation not done yet")
            return None
        
        start: Point2 = self.bunker_forward
        
        # Calculate preferred direction away from CC toward opponent
        opponent_position: Point2 = self.bot.enemy_start_locations[0]
        return dfs_in_pathing(self.bot, start, UnitTypeId.BUNKER, opponent_position)

    @cached_property
    def bunker_forward(self) -> Point2:
        map_center: Point2 = self.bot.game_info.map_center
        bunker_position: Point2 = self.position.towards(map_center, 3)
        # if there's a ramp descending, position the bunker in top of it
        ramps: List[Ramp] = self.bot.game_info.map_ramps
        for ramp in ramps:
            if (
                ramp.top_center.distance_to(self.position) < ramp.bottom_center.distance_to(self.position)
                and ramp.top_center.distance_to(self.position) <= 15
            ):
                bunker_position = center([self.position, ramp.top_center])
        return bunker_position.rounded_half
    
    @custom_cache_once_per_frame
    def bunker_ramp(self) -> Optional[Point2]:
        if (self.is_main == True):
            # prefered_position: Point2 = self.bot.main_base_ramp.top_center
            depot_walls: List[Point2] = list(self.bot.main_base_ramp.corner_depots)
            closest_depot_wall: Point2 = closest_point(self.position, depot_walls)
            return dfs_in_pathing(self.bot, closest_depot_wall, UnitTypeId.BUNKER, self.position)
        closest_ramp_bottom: Point2 = find_closest_bottom_ramp(self.bot, self.position).bottom_center
        if (self.position.distance_to(closest_ramp_bottom) >= 15):
            return None
        enemy_spawn: Point2 = self.bot.enemy_start_locations[0]
        bunker_position: Point2 = center([self.position, closest_ramp_bottom])
        if (bunker_position):
            bunker_position = bunker_position.towards(enemy_spawn)
        direction_vector = self.position - closest_ramp_bottom
        preferred_direction = Point2((-direction_vector.x, -direction_vector.y))  # Invert to move away
        return dfs_in_pathing(self.bot, bunker_position.rounded_half, UnitTypeId.BUNKER, preferred_direction)
    
    @custom_cache_once_per_frame
    def bunker_position(self) -> Point2:
        if (self.is_main):
            return self.bunker_ramp
        return self.bunker_forward_in_pathing
    
    def compute_bunker_mining_position(self) -> None:
        """
        Called once by the buildings layer, after the static blockers (minerals, geysers, rocks)
        are set but before the mineral lines are reserved, so the DFS can land between the geysers.
        """
        if (not self.can_bunker_mine):
            return
        # preferred: glued to the townhall (the workers drop their vespene right out of the bunker)
        glued_position: Optional[Point2] = self._glued_bunker_mining_position()
        if (glued_position is not None):
            self.bunker_mining_position = glued_position
            return

        # fallback: closest buildable position between the geysers and the townhall
        points: List[Point2] = [geyser.position for geyser in self.vespene_geysers]
        points.append(self.position)
        target: Optional[Point2] = center(points)
        if (target is None):
            return
        # the bunker's 3x3 footprint can't overlap the townhall's 5x5 footprint
        min_offset: float = self.FOOTPRINT_RADIUS + BUNKER_RADIUS

        def overlaps_townhall(position: Point2) -> bool:
            return (
                abs(position.x - self.position.x) < min_offset
                and abs(position.y - self.position.y) < min_offset
            )

        # search away from the townhall
        preferred_direction: Point2 = target + (target - self.position)
        self.bunker_mining_position = dfs_in_pathing(
            self.bot,
            target,
            UnitTypeId.BUNKER,
            preferred_direction,
            reject=overlaps_townhall,
        )

    def _glued_bunker_mining_position(self) -> Optional[Point2]:
        """
        Bunker touching a side of the townhall on BUNKER_MINING_CONTACT_TILES tiles (the layout measured as the best),
        the buildable one closest to both geysers. None if none is buildable.
        """
        # centers distance when the footprints touch (5x5 townhall, 3x3 bunker)
        touching_offset: float = self.FOOTPRINT_RADIUS + BUNKER_RADIUS
        # offset along the touching side: 1 contact tile = shifted as far as possible towards the corner
        side_offset: float = touching_offset - BUNKER_MINING_CONTACT_TILES
        candidates: List[Point2] = []
        for touching_sign in (-1, 1):
            for side_sign in (-1, 1):
                # left / right sides, then bottom / top sides
                candidates.append(self.position + Point2((touching_sign * touching_offset, side_sign * side_offset)))
                candidates.append(self.position + Point2((side_sign * side_offset, touching_sign * touching_offset)))
        buildable: List[Point2] = [
            candidate for candidate in candidates
            if valid_building_position(self.bot, candidate, UnitTypeId.BUNKER, BUNKER_RADIUS, False)
        ]
        if (len(buildable) == 0):
            return None
        return min(
            buildable,
            key=lambda candidate: sum(candidate.distance_to(geyser) for geyser in self.vespene_geysers),
        )

    @custom_cache_once_per_frame
    def bunker_mining_unit(self) -> Optional[Unit]:
        if (self.bunker_mining_position is None):
            return None
        bunkers: Units = self.bot.structures(UnitTypeId.BUNKER).filter(
            lambda bunker: bunker.distance_to(self.bunker_mining_position) < 1
        )
        if (bunkers.amount >= 1):
            return bunkers.first
        return None
    
    @custom_cache_once_per_frame
    def turret_mineral_line(self) -> Point2:
        if (self.mineral_fields.amount == 0):
            return self.mineral_line
        central_mineral_field: Unit = self.mineral_fields.closest_to(self.mineral_line)
        return central_mineral_field.position.towards(self.position)
    
    @custom_cache_once_per_frame
    def turret_wall_position(self) -> Point2:
        if (self.is_main):
            return Point2(self.bunker_ramp.towards(self.position, 2)).rounded
        return center([self.position, self.bunker_position])
    
    @custom_cache_once_per_frame
    def defending_structure(self) -> Optional[Unit]:
        if (self.has_defensive_structure == False):
            return None
        return self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).ready.closest_to(self.position)
    
    @custom_cache_once_per_frame
    def is_fully_scouted(self) -> bool:
        return len(self.unscouted_points) == 0
    
    @custom_cache_once_per_frame
    def unscouted_points(self) -> List[Point2]:
        """
        Unscouted, pathable points within a circle of radius around the position, at the same terrain height.
        A point that has been seen once (visibility != 0) can never become unseen again,
        so seen points are dropped for good and the candidate list shrinks over the game.
        """
        if (self._unscouted_candidates is None):
            self._unscouted_candidates = same_height_points_around(self.bot, self.position, self.radius)
        visibility = self.bot.state.visibility
        self._unscouted_candidates = [point for point in self._unscouted_candidates if visibility[point] == 0]
        return [point for point in self._unscouted_candidates if self.bot.in_pathing_grid(point)]
    
    @custom_cache_once_per_frame
    def is_potentially_enemy(self):
        """
        Updated each frame with suspicions of base taken
        """
        if (self.is_enemy):
            self._potentially_enemy = True
        elif (self.is_taken):
            self._potentially_enemy = False
        elif (self.is_visible):
            self._potentially_enemy = False
        return self._potentially_enemy
    
    def in_pathing(self, target: Point2) -> Point2:
        # Convert target to the nearest grid-aligned integer point
        start = Point2((round(target.x), round(target.y)))

        # If already valid, return it
        if self.bot.in_placement_grid(start):
            return start
        
        # Calculate preferred direction away from CC toward opponent
        opponent_position: Point2 = self.bot.enemy_start_locations[0]
        direction_vector = opponent_position - self.position
        preferred_direction = Point2((-direction_vector.x, -direction_vector.y))  # Invert to move away

        # Normalize to get step direction (either -1, 0, or 1)
        step_x = 1 if preferred_direction.x > 0 else -1 if preferred_direction.x < 0 else 0
        step_y = 1 if preferred_direction.y > 0 else -1 if preferred_direction.y < 0 else 0

        # BFS search for the nearest valid point
        search_queue = deque([start])
        visited = set([start])

        # Prioritized search directions (biased away from CC)
        directions = [(step_x, step_y)]  # Move in the preferred direction first
        directions += [(1, 0), (-1, 0), (0, 1), (0, -1)]  # Then check standard directions

        while search_queue:
            current = search_queue.popleft()

            for dx, dy in directions:
                neighbor = Point2((current.x + dx, current.y + dy))
                
                if neighbor in visited:
                    continue  # Skip already checked locations
                
                visited.add(neighbor)

                # Stay inside the map (in_placement_grid asserts on out-of-bounds points)
                if not (
                    0 <= neighbor.x < self.bot.game_info.placement_grid.width
                    and 0 <= neighbor.y < self.bot.game_info.placement_grid.height
                ):
                    continue

                # If it's a valid buildable position, return it
                if self.bot.in_placement_grid(neighbor):
                    return neighbor

                # Otherwise, continue expanding
                search_queue.append(neighbor)

        # If no valid point is found (unlikely), return the original position
        return start
    
    def update_scout_status(self):
        if (self.bot.state.visibility[self.position.rounded] == 2):
            self.last_scouted = self.bot.time

        # suspect that bases around creep are taken
        map: MapData = get_map(self.bot)
        EXPANSION_SUSPECTED_THRESHOLD: int = 10
        ASSUME_DELAY: float = 20
        creep_distance: float = map.influence_maps.creep.distance_to_creep[self.position]
        if (
            not self.is_visible
            and self.last_scouted + ASSUME_DELAY < self.bot.time
            and creep_distance < EXPANSION_SUSPECTED_THRESHOLD
        ):
            self._potentially_enemy = True