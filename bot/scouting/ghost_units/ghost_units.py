from __future__ import annotations
from typing import Any, Callable, Generator, List, Optional, Set

from attr import dataclass
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

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
    def tags(self) -> Set[int]:
        """ Returns all unit tags as a set. """
        return {ghost.tag for ghost in self.ghost_units}
    
    @property
    def not_flying(self) -> GhostUnits:
        return self.filter(lambda ghost: not ghost.is_flying)
    
    @property
    def flying(self) -> GhostUnits:
        return self.filter(lambda ghost: ghost.is_flying)
    