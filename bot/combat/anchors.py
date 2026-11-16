from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Callable, List, Optional, TYPE_CHECKING

from bot.scouting.ghost_units.ghost_units import GhostUnit
from bot.utils.unit_functions import calculate_bunker_range
from bot.utils.unit_supply import get_unit_value
from bot.utils.unit_tags import changelings, dont_attack, menacing
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit

if TYPE_CHECKING:
    from bot.superbot import Superbot  # typing only: avoids a circular import


# Anchors are our units that hold ground: sieged tanks, planetary fortresses and loaded bunkers.
# A unit is "covered" by an anchor when any ground enemy able to shoot it has to stand
# inside the anchor's range to do so. Worst case, the enemy stands on the far side of the unit:
#   d(anchor, unit) + unit_radius + enemy_range + enemy_radius <= anchor_reach + enemy_radius
#   => d(anchor, unit) <= anchor_reach - enemy_range - unit_radius - margin
# where anchor_reach = anchor radius + anchor range (center to enemy edge): the enemy radius cancels out.
#
# Most fights are directional: when the local enemies come from one side, we assume they stay in front
# of a line drawn FLANK_TOLERANCE behind the anchor. Only firing positions on their side count, so the
# covered zone extends behind the anchor (up to BACK_LIMIT, to keep protecting it) instead of being a disk.

# Usable depth (beyond the anchor's own body) under which the covered zone is too small to shelter units
MIN_DEPTH: float = 1.5
TANK_MARGIN: float = 0.5
STRUCTURE_MARGIN: float = 0.25
TANK_RANGE: float = 13
# Enemies further than reach + this distance from the anchor don't shrink its zone
ENEMY_SEARCH_DISTANCE: float = 10
# Above this share of air ground-attackers in the local threat, ground anchors stop being a refuge
AIR_THREAT_RATIO: float = 0.3
# Keep the cover point a bit inside the zone to avoid oscillating on its edge
COVER_INNER_OFFSET: float = 0.5
# How far behind the anchor the enemy may still reach to flank us
FLANK_TOLERANCE: float = 2
# Leash: the directional zone stops this far behind the anchor, so units kiting back don't leave it alone
# (never smaller than the undirected zone)
BACK_LIMIT: float = 8
# Concentration (0: enemies all around, 1: all in the same direction) under which the fight isn't directional
MIN_THREAT_CONCENTRATION: float = 0.5
# Binary search iterations to find the edge of the covered zone
COVER_SEARCH_STEPS: int = 8

# Ranges the API doesn't report (spells, burrowed or unsieged forms, unknown upgrades):
# the max is strict, so we assume the longest range the unit can get
ENEMY_GROUND_RANGE_OVERRIDES: dict[UnitTypeId, float] = {
    UnitTypeId.SIEGETANK: 13,
    UnitTypeId.SIEGETANKSIEGED: 13,
    UnitTypeId.LURKERMP: 10,
    UnitTypeId.LURKERMPBURROWED: 10,
    UnitTypeId.WIDOWMINE: 5,
    UnitTypeId.WIDOWMINEBURROWED: 5,
    UnitTypeId.RAVAGER: 9,
    UnitTypeId.HIGHTEMPLAR: 9,
    UnitTypeId.INFESTOR: 10,
    UnitTypeId.INFESTORBURROWED: 10,
    UnitTypeId.HYDRALISK: 6,
    UnitTypeId.COLOSSUS: 9,
    UnitTypeId.CYCLONE: 7,
}


def enemy_ground_range(enemy: Unit | GhostUnit) -> float:
    return max(ENEMY_GROUND_RANGE_OVERRIDES.get(enemy.type_id, 0), enemy.ground_range)

def is_ground_attacker(enemy: Unit | GhostUnit) -> bool:
    return (
        not enemy.is_flying
        and (enemy.can_attack_ground or enemy.type_id in menacing or enemy.type_id in ENEMY_GROUND_RANGE_OVERRIDES)
    )

def is_air_attacker(enemy: Unit | GhostUnit) -> bool:
    # ground anchors can't shoot them: covering doesn't apply
    return (
        enemy.is_flying
        and (enemy.can_attack_ground or enemy.type_id in menacing)
    )


@dataclass
class Anchor:
    unit: Unit
    # anchor radius + ground range
    reach: float
    margin: float
    # longest ground range among local enemies (strict max)
    enemy_range: float
    air_threatened: bool
    # unit vector from the anchor towards the local ground enemies, None if they surround it (or there is none)
    threat_direction: Optional[Point2] = None

    @property
    def position(self) -> Point2:
        return self.unit.position

    @property
    def depth(self) -> float:
        """Usable depth of the covered zone, beyond the anchor's own body"""
        return self.reach - self.unit.radius - self.enemy_range - self.margin

    @property
    def is_valid(self) -> bool:
        return self.depth >= MIN_DEPTH and not self.air_threatened

    def cover_radius(self, unit_radius: float = 0) -> float:
        """Max distance between the anchor and a unit's center for the unit to be covered"""
        return self.reach - self.enemy_range - self.margin - unit_radius

    def covers(self, position: Point2, unit_radius: float = 0) -> bool:
        reach: float = self.reach - self.margin
        # enemies able to shoot the unit stand within this distance of its center
        threat_radius: float = self.enemy_range + unit_radius
        dx: float = position.x - self.position.x
        dy: float = position.y - self.position.y
        distance: float = math.hypot(dx, dy)

        if (self.threat_direction is None or distance == 0):
            return distance + threat_radius <= reach

        direction: Point2 = self.threat_direction
        # coordinates in the fight frame: along the threat direction and across it
        along: float = dx * direction.x + dy * direction.y
        across: float = -dx * direction.y + dy * direction.x
        # past the leash, the unit is only covered if it would be in an undirected fight
        if (along < -BACK_LIMIT):
            return distance + threat_radius <= reach

        # the farthest firing position from the anchor is behind the unit, in the anchor-unit direction
        farthest_along: float = along + threat_radius * along / distance
        if (farthest_along >= -FLANK_TOLERANCE):
            return distance + threat_radius <= reach

        # enemies can't get there: only firing positions in front of the flank line count
        if (along + threat_radius < -FLANK_TOLERANCE):
            return True

        # the farthest firing position is where the threat circle crosses the flank line
        offset: float = -FLANK_TOLERANCE - along
        half_chord: float = math.sqrt(max(0, threat_radius ** 2 - offset ** 2))
        farthest_distance: float = math.hypot(FLANK_TOLERANCE, abs(across) + half_chord)
        return farthest_distance <= reach

    def distance_to_zone(self, position: Point2, unit_radius: float = 0) -> float:
        if (self.covers(position, unit_radius)):
            return 0
        return max(0, self.position.distance_to(position) - self.cover_radius(unit_radius))

    def closest_covered_point(self, destination: Point2, unit_radius: float = 0) -> Point2:
        """
        Last covered point on the segment from the anchor to the destination.
        The zone is star-shaped around the anchor, so a binary search finds its edge.
        """
        if (self.covers(destination, unit_radius)):
            return destination
        distance: float = self.position.distance_to(destination)
        covered: float = 0
        uncovered: float = distance
        for _ in range(COVER_SEARCH_STEPS):
            middle: float = (covered + uncovered) / 2
            if (self.covers(self.position.towards(destination, middle), unit_radius)):
                covered = middle
            else:
                uncovered = middle
        return self.position.towards(destination, max(0, covered - COVER_INNER_OFFSET))


class Anchors(CachedClass):
    bot: Superbot

    @custom_cache_once_per_frame
    def all(self) -> List[Anchor]:
        anchors: List[Anchor] = []
        hisec: bool = self.bot.already_pending_upgrade(UpgradeId.HISECAUTOTRACKING) == 1

        for tank in self.bot.units(UnitTypeId.SIEGETANKSIEGED):
            tank_range: float = tank.ground_range if tank.ground_range > 0 else TANK_RANGE
            anchors.append(self._create_anchor(tank, tank.radius + tank_range, TANK_MARGIN))

        for pf in self.bot.structures(UnitTypeId.PLANETARYFORTRESS).ready:
            pf_range: float = pf.ground_range + (1 if hisec else 0)
            anchors.append(self._create_anchor(pf, pf.radius + pf_range, STRUCTURE_MARGIN))

        for bunker in self.bot.structures(UnitTypeId.BUNKER):
            if (bunker.build_progress < 0.95 or bunker.cargo_used == 0):
                continue
            # already measured from the bunker's center
            bunker_ground_range, _ = calculate_bunker_range(self.bot, bunker)
            anchors.append(self._create_anchor(bunker, bunker_ground_range, STRUCTURE_MARGIN))

        return anchors

    @custom_cache_once_per_frame
    def valid(self) -> List[Anchor]:
        return [anchor for anchor in self.all if anchor.is_valid]

    def _create_anchor(self, unit: Unit, reach: float, margin: float) -> Anchor:
        search_distance: float = reach + ENEMY_SEARCH_DISTANCE
        local_enemies: List[Unit | GhostUnit] = [
            enemy for enemy in self.bot.enemy_units
            if (
                enemy.type_id not in changelings
                and enemy.type_id not in dont_attack
                and enemy.distance_to(unit) <= search_distance
            )
        ]
        local_enemies += [
            ghost for ghost in self.bot.ghost_units.assumed_enemy_units
            if ghost.position.distance_to(unit.position) <= search_distance
        ]

        ground_attackers: List[Unit | GhostUnit] = [enemy for enemy in local_enemies if is_ground_attacker(enemy)]
        air_attackers: List[Unit | GhostUnit] = [enemy for enemy in local_enemies if is_air_attacker(enemy)]

        enemy_range: float = max((enemy_ground_range(enemy) for enemy in ground_attackers), default=0)

        ground_supply: float = sum(get_unit_value(enemy) for enemy in ground_attackers)
        air_supply: float = sum(get_unit_value(enemy) for enemy in air_attackers)
        total_supply: float = ground_supply + air_supply
        air_threatened: bool = total_supply > 0 and air_supply / total_supply >= AIR_THREAT_RATIO

        threat_direction: Optional[Point2] = self._threat_direction(unit.position, ground_attackers)
        return Anchor(unit, reach, margin, enemy_range, air_threatened, threat_direction)

    def _threat_direction(self, position: Point2, enemies: List[Unit | GhostUnit]) -> Optional[Point2]:
        # supply weighted mean of the unit vectors towards the enemies:
        # its length measures how much they come from the same side
        sum_x: float = 0
        sum_y: float = 0
        total_weight: float = 0
        for enemy in enemies:
            dx: float = enemy.position.x - position.x
            dy: float = enemy.position.y - position.y
            distance: float = math.hypot(dx, dy)
            if (distance == 0):
                continue
            weight: float = max(get_unit_value(enemy), 0.5)
            sum_x += weight * dx / distance
            sum_y += weight * dy / distance
            total_weight += weight
        if (total_weight == 0):
            return None
        length: float = math.hypot(sum_x, sum_y)
        if (length / total_weight < MIN_THREAT_CONCENTRATION):
            return None
        return Point2((sum_x / length, sum_y / length))

    def valid_near(self, position: Point2, distance: float, unit_radius: float = 0) -> List[Anchor]:
        """Valid anchors whose covered zone is within distance of the position"""
        return [
            anchor for anchor in self.valid
            if anchor.distance_to_zone(position, unit_radius) <= distance
        ]

    def cover_point(self, destination: Point2, unit: Unit, max_distance: float) -> Optional[Point2]:
        """
        Closest covered point to the destination, among the valid anchors whose zone is within
        max_distance of the unit. None if there is none: the unit is free to go anywhere.
        Returns the destination itself if it's already covered.
        """
        anchors: List[Anchor] = self.valid_near(unit.position, max_distance, unit.radius)
        if (len(anchors) == 0):
            return None
        if (any(anchor.covers(destination, unit.radius) for anchor in anchors)):
            return destination
        candidates: List[Point2] = [anchor.closest_covered_point(destination, unit.radius) for anchor in anchors]
        return min(candidates, key=lambda point: point.distance_to(destination))

    def covered_filter(self, unit: Unit, max_distance: float) -> Optional[Callable[[Point2], bool]]:
        """
        Tile filter keeping the positions covered by the valid anchors close to the unit.
        None if there is none: the unit is free to go anywhere.
        """
        anchors: List[Anchor] = self.valid_near(unit.position, max_distance, unit.radius)
        if (len(anchors) == 0):
            return None
        unit_radius: float = unit.radius
        return lambda position: any(anchor.covers(position, unit_radius) for anchor in anchors)

    def engaged_anchor(self, unit: Unit, enemy: Unit, max_distance: float) -> Optional[Anchor]:
        """
        A directional anchor close to the unit that the enemy has walked into the range of:
        the unit should kite back to draw the enemy deeper. None otherwise.
        """
        anchors: List[Anchor] = [
            anchor for anchor in self.valid_near(unit.position, max_distance, unit.radius)
            if (
                anchor.threat_direction is not None
                and anchor.position.distance_to(enemy) <= anchor.reach + enemy.radius
            )
        ]
        if (len(anchors) == 0):
            return None
        return min(anchors, key=lambda anchor: anchor.position.distance_to(unit))
