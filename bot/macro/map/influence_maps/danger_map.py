import math
from typing import List

import numpy as np
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from bot.scouting.ghost_units.ghost_units import GhostUnit, GhostUnits
from bot.utils.point2_functions.utils import center
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ....utils.unit_tags import tower_types

class DangerMap:
    """
    Computes per-unit danger and applies wall/blocking modifiers when asked.
    Contains two InfluenceMaps: ground and air.
    """
    bot: BotAI
    ground: InfluenceMap
    ground_terrain: InfluenceMap
    air: InfluenceMap
    FALLOFF_LEVELS: List[tuple[float, float]] = [
        (1.00, 1.0),   # inside range
        (0.50, 2.0),   # medium threat
        (0.25, 4.0),   # low threat
        (0.05, 8.0),   # very low threat
    ]
    
    def __init__(
        self,
        bot: BotAI,
        map: np.ndarray = None
    ):
        self.bot = bot
        self.ground = InfluenceMap(bot, map)
        self.ground_terrain = InfluenceMap(bot, map)
        self.air = InfluenceMap(bot)

    def reset(self):
        self.ground.map[:] = 0
        self.ground_terrain.map[:] = 0
        self.air.map[:] = 0

    def get_unit_property(self, unit: Unit) -> tuple[Point2, float, float, float, float, float, float, float]:
        RADIUS_BUFFER: float = 1.1
        
        position: Point2 = unit.position
        radius: float = unit.radius * RADIUS_BUFFER
        ground_dps: float = unit.ground_dps
        ground_range: float = unit.ground_range
        air_dps: float = unit.air_dps
        air_range: float = unit.air_range
        movement_speed: float = unit.real_speed * 1.4
        minimum_range: float = 0

        # melee unit don't have exactly 0 range
        if (unit.can_attack_ground and ground_range == 0):
            ground_range = 1

        match(unit.type_id):
            case UnitTypeId.BUNKER:
                # assume 2 marines inside
                ground_dps = 20
                ground_range = 7
            case UnitTypeId.SIEGETANKSIEGED:
                minimum_range = 2
            case UnitTypeId.DISRUPTORPHASED:
                ground_dps = 100
                ground_range = 1.5
            case UnitTypeId.BANELING:
                ground_dps = 30
                ground_range += 2.2
            case UnitTypeId.ADEPTPHASESHIFT:
                ground_dps = 10
                ground_range = 4
            case UnitTypeId.LIBERATORAG:
                ground_dps = 0
            case UnitTypeId.CARRIER:
                # zone around carrier is dangerous
                ground_dps = 25
                ground_range = 12
                air_range = 12
            case _:
                pass

        return (
            position,
            radius,
            ground_dps,
            ground_range,
            air_dps,
            air_range,
            movement_speed,
            minimum_range
        )

    def update(self, include_structures: bool = True):
        self.reset()
        units: Units = self.bot.enemy_units
        if (include_structures):
            units += self.bot.enemy_structures(tower_types)
        
        for unit in units:
            self.update_unit(unit)

        ghost_units: GhostUnits = self.bot.ghost_units.assumed_enemy_units
        for ghost in ghost_units:
            self.update_unit(ghost)
    
    def update_unit(self, unit: Unit | GhostUnit):
        (
            unit_position,
            unit_radius,
            ground_dps,
            ground_range,
            air_dps,
            air_range,
            move_speed,
            minimum_range,
        ) = self.get_unit_property(unit)

        for weight, ms_factor in self.FALLOFF_LEVELS:
            ground_radius = unit_radius + ground_range + move_speed * ms_factor / 2
            air_radius = unit_radius + air_range + move_speed * ms_factor / 2
            effective_min_radius: float = unit_radius + minimum_range  if (minimum_range > 0) else 0
            self.ground.update(unit_position, ground_radius, ground_dps * weight, effective_min_radius)
            self.air.update(unit_position, air_radius, air_dps * weight, effective_min_radius)


    def apply_wall_and_blocking(self, wall_distance: np.ndarray, block_mask: np.ndarray):
        # === Wall Danger ===
        # Distance 0 → unpathable → 999
        # Distance 1 → dangerous * 0.5
        # Distance 2 → dangerous * 0.25
        # >2 → safe-ish

        self.ground_terrain.map[:] = self.ground.map.copy()
        self.ground_terrain.map += np.where(
            wall_distance == 0,
            999,
            np.exp(-wall_distance * 0.75) * 5.0
        )
        # absolute blockers
        self.ground_terrain.map[block_mask] = 999