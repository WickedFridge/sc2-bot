from typing import List
from sc2.data import Race

import enum

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class Posture(enum.Enum):
    AGRESSIVE = 0
    NEUTRAL = 1
    DEFENSIVE = 2

class Position(enum.Enum):
    AHEAD = 0
    EVEN = 1
    BEHIND = 2

class Opponent:
    race: Race
    posture: Posture = Posture.NEUTRAL
    position: Position = Position.EVEN
    known_tech: List[UnitTypeId|UpgradeId]
