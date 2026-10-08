from __future__ import annotations
from typing import Any, Callable, Generator, List, Optional, Set

from attr import dataclass
from sc2.bot_ai import BotAI
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ...utils.point2_functions.utils import center
from ...utils.unit_tags import burrowed_units

@dataclass
class GhostUnit:
    tag: int
    type_id: UnitTypeId
    position: Point2
    radius: float
    ground_dps: float
    ground_range: float
    air_dps: float
    air_range: float
    real_speed: float
    health: float
    health_max: float
    health_percentage: float
    shield: float
    shield_max: float
    shield_percentage: float
    energy: float
    energy_max: float
    energy_percentage: float
    is_flying: bool
    is_armored: bool
    can_attack: bool
    can_attack_ground: bool
    can_attack_air: bool
    last_seen_frame: int
    expiry_frame: int
    is_cloaked: bool
    is_visible: bool
    is_possibly_hidden: bool = False
    is_enemy: bool = True
    passengers: Set[Unit] = set()

    def has_buff(self, buff_id: BuffId) -> bool:
        """ Checks if the ghost unit has a specific buff. """
        # Since we don't have actual buffs for ghost units, this is a placeholder.
        # In a real implementation, you would track buffs on ghost units as well.
        return False
    
    @property
    def name(self) -> str:
        return self.type_id.name
    
    @property
    def is_burrowed(self) -> bool:
        return self.type_id in burrowed_units

class GhostUnits:
    """
    Lightweight Units-like container for enemy units no longer in vision.
    Safe for estimation, danger maps, and strategic reasoning only.
    """
    bot: BotAI
    ghost_units: List[GhostUnit]

    def __init__(self, bot: BotAI, ghost_units: Optional[List[GhostUnit]] = None):
        self.bot = bot
        self.ghost_units = ghost_units or []

    def __iter__(self) -> Generator[GhostUnit, None, None]:
        return iter(self.ghost_units)
    
    def __len__(self) -> int:
        return len(self.ghost_units)

    def __getitem__(self, index: int) -> GhostUnit:
        return self.ghost_units[index]
    
    def __add__(self, other: GhostUnits) -> GhostUnits:
        if not isinstance(other, GhostUnits):
            return NotImplemented
        return GhostUnits(self.bot, self.ghost_units + other.ghost_units)
    
    def __iadd__(self, other: GhostUnits) -> GhostUnits:
        if not isinstance(other, GhostUnits):
            return NotImplemented
        self.ghost_units.extend(other.ghost_units)
        return self
    
    def __call__(self, type_id: UnitTypeId) -> GhostUnits:
        return self.filter(lambda g: g.type_id == type_id)

    @property
    def amount(self) -> int:
        return len(self.ghost_units)
    
    def add(self, ghost_unit: GhostUnit) -> None:
        self.ghost_units.append(ghost_unit)

    def extended(self, ghost_unit_list: List[GhostUnit]) -> GhostUnits:
        return GhostUnits(self.bot, self.ghost_units.copy() + ghost_unit_list)
    
    def filter(self, pred: Callable[[GhostUnit], Any]) -> GhostUnits:
        return GhostUnits(self.bot, list(filter(pred, self)))
    
    def copy(self) -> GhostUnits:
        return GhostUnits(self.bot, self.ghost_units.copy())
    
    def sort(self, key: Optional[Callable[[GhostUnit], Any]] = None, reverse: bool = False) -> None:
        self.ghost_units.sort(key=key, reverse=reverse)

    def sorted(self, key: Optional[Callable[[GhostUnit], Any]] = None, reverse: bool = False) -> GhostUnits:
        sorted_ghost_units = sorted(self.ghost_units, key=key, reverse=reverse)
        return GhostUnits(self.bot, sorted_ghost_units)
    
    def take(self, n: int) -> GhostUnits:
        return GhostUnits(self.bot, self.ghost_units[:n])

    def closest_to(self, position: Point2 | Unit) -> GhostUnit:
        if (not self.ghost_units):
            raise ValueError("No ghost units available")
        point: Point2 = position.position if isinstance(position, Unit) else position
        return min(self.ghost_units, key=lambda g: g.position.distance_to(point))
    
    def closer_than(self, distance: float, position: Point2 | Unit) -> GhostUnits:
        point: Point2 = position.position if isinstance(position, Unit) else position
        return self.filter(lambda g: g.position.distance_to(point) < distance)
    
    def in_distance_of_group(self, other_units: Units, distance: float) -> GhostUnits:
        """Returns ghost units that are closer than distance from any unit in the other units object.

        :param other_units:
        :param distance:
        """
        assert other_units, "Other units object is empty"
        # Return self because there are no ghosts
        if not self:
            return self
        distance_squared = distance**2
        # Ghosts aren't in the bot's pdist cache, so compute distances from raw positions
        other_positions = [other_unit.position_tuple for other_unit in other_units]
        return self.filter(
            lambda ghost: any(
                self.bot.distance_math_hypot_squared(ghost.position, other_position) < distance_squared
                for other_position in other_positions
            )
        )
    
    def find_by_tag(self, tag: int) -> Optional[GhostUnit]:
        """
        :param tag:
        """
        for ghost in self.ghost_units:
            if (ghost.tag == tag):
                return ghost
        return None
    
    @property
    def first(self) -> GhostUnit:
        return self.ghost_units[0]
    
    @property
    def center(self) -> Point2:
        """ Returns the central position of all ghost units. """
        assert self.ghost_units, "Ghost units object is empty"
        ghosts_center: Optional[Point2] = center([ghost.position for ghost in self.ghost_units])
        assert ghosts_center is not None
        return ghosts_center

    @property
    def tags(self) -> Set[int]:
        """ Returns all unit tags as a set. """
        return {ghost.tag for ghost in self.ghost_units}
    
    @property
    def not_flying(self) -> GhostUnits:
        return self.filter(lambda ghost: not ghost.is_flying)
    
    @property
    def flying(self) -> GhostUnits:
        return self.filter(lambda ghost: ghost.is_flying)
    