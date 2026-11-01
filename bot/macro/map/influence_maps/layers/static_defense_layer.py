from typing import Optional

import numpy as np
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit


class StaticDefenseLayer:
    """
    Areas covered by enemy static defenses, one map for ground units and one for air units.
    Each tile counts the number of towers covering it (0 = safe).
    """
    bot: BotAI
    ground: InfluenceMap
    air: InfluenceMap
    # Worst case ranges (upgrades assumed), from the edge of the structure
    # python-sc2 gives 0 range to bunkers, and we can't see if an enemy bunker is loaded
    GROUND_RANGE: dict[UnitTypeId, float] = {
        UnitTypeId.PHOTONCANNON: 7,
        UnitTypeId.SPINECRAWLER: 7,
        UnitTypeId.BUNKER: 6,               # marine 5 + 1
        UnitTypeId.PLANETARYFORTRESS: 7,    # 6 + Hi-Sec Auto Tracking
    }
    AIR_RANGE: dict[UnitTypeId, float] = {
        UnitTypeId.PHOTONCANNON: 7,
        UnitTypeId.SPORECRAWLER: 7,
        UnitTypeId.MISSILETURRET: 8,        # 7 + Hi-Sec Auto Tracking
        UnitTypeId.BUNKER: 6,               # marine 5 + 1
    }
    # covers the radius of our units + tile rounding
    SAFETY_MARGIN: float = 1.5
    # Structures almost done are already considered dangerous
    BUILD_PROGRESS_THRESHOLD: float = 0.95

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.ground = InfluenceMap(bot)
        self.air = InfluenceMap(bot)

    def update(self):
        self.ground.reset()
        self.air.reset()
        # enemy_structures includes snapshots, so we remember towers in the fog
        for structure in self.bot.enemy_structures:
            if (structure.build_progress < self.BUILD_PROGRESS_THRESHOLD):
                continue
            if (structure.type_id in self.GROUND_RANGE):
                radius: float = structure.radius + self.GROUND_RANGE[structure.type_id] + self.SAFETY_MARGIN
                self.ground.update(structure.position, radius, 1, density_alpha=0)
            if (structure.type_id in self.AIR_RANGE):
                radius: float = structure.radius + self.AIR_RANGE[structure.type_id] + self.SAFETY_MARGIN
                self.air.update(structure.position, radius, 1, density_alpha=0)

    def map_for(self, flying: bool) -> InfluenceMap:
        return self.air if flying else self.ground

    def covers(self, position: Point2, flying: bool) -> bool:
        return self.map_for(flying)[position] > 0

    def closest_safe_spot(self, unit: Unit, search_radius: float = 12) -> Optional[Point2]:
        """Closest tile out of static defense range (and pathable for ground units)."""
        influence_map: InfluenceMap = self.map_for(unit.is_flying)
        x1, y1, x2, y2, submap, dist = influence_map._region(unit.position, search_radius)
        valid: np.ndarray = (submap == 0) & (dist <= search_radius)
        if (not unit.is_flying):
            pathing: np.ndarray = self.bot.game_info.pathing_grid.data_numpy[y1:y2, x1:x2]
            valid &= (pathing != 0)
        if (not valid.any()):
            return None
        masked_dist: np.ndarray = np.where(valid, dist, np.inf)
        iy, ix = np.unravel_index(masked_dist.argmin(), masked_dist.shape)
        return Point2((x1 + ix, y1 + iy))
