import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt

from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI
from sc2.position import Point2


class CreepLayer:
    creep: InfluenceMap                  # boolean mask
    density: InfluenceMap                # float32, smoothed creep
    bonus: InfluenceMap                  # float32, bonus danger by creep
    distance_to_creep: InfluenceMap      # float32, grid of distances to nearest creep
    CREEP_BONUS: float = 1.2

    def __init__(self, bot: BotAI):
        self.bot = bot

        # Will be filled every frame
        self.creep: InfluenceMap = None                # bool mask shape [h,w]
        self.density: InfluenceMap = None              # float32
        self.distance_to_creep: InfluenceMap = None    # float32
    
    def update(self) -> None:
        # 1) Read creep from SC2
        creep_raw: np.ndarray = self.bot.state.creep.data_numpy.astype(np.float32)
        self.creep = InfluenceMap(self.bot, (creep_raw == 1), dtype=np.float32)

        # 2) Smooth creep => density (float32)
        # Gaussian blur gives "probability" of tumor locations
        self.density = InfluenceMap(self.bot, gaussian_filter(self.creep.map.astype(np.float32), sigma=2.0), dtype=np.float32)

        # 3) Compute distance-to-nearest-creep map
        # Invert creep: distance_transform_edt gives 0 on creep, >0 elsewhere
        self.distance_to_creep = InfluenceMap(self.bot, distance_transform_edt(self.creep.inverted).astype(np.float32), dtype=np.float32)

        # 4) Precompute bonus map (faster than calling creep_bonus inside loops)
        self.bonus = InfluenceMap(self.bot, np.where(self.creep.map, self.CREEP_BONUS, 1.0).astype(np.float32), dtype=np.float32)
    
    # ----------------------------------------------------------
    # Simple queries
    # ----------------------------------------------------------
    def on_creep(self, x: int, y: int) -> bool:
        return bool(self.creep[y, x])

    def creep_bonus(self, x: int, y: int) -> float:
        """Return multiplier to danger: 1.2 if on creep, else 1.0"""
        return 1.2 if self.creep[y, x] else 1.0

    def get_density(self, x: int, y: int) -> float:
        """How 'likely' we expect a creep tumor to be here."""
        return float(self.density[y, x])
    
    # ----------------------------------------------------------
    # Nearest creep tile to a given position
    # ----------------------------------------------------------
    def closest_creep(self, pos: Point2) -> Point2 | None:
        """
        Returns the closest creep tile using the precomputed distance map.
        Very fast.
        """
        # If already on creep, return the same tile
        if self.creep[pos]:
            return pos
        
        # Convert to int grid coordinates
        x0: float = pos.x
        y0: float = pos.y
        
        # (1) Find all creep tiles
        ys, xs = np.where(self.creep.map)
        if len(xs) == 0:
            return None

        # (2) Compute squared distances
        dx = xs - x0
        dy = ys - y0
        dist2 = dx * dx + dy * dy

        idx = np.argmin(dist2)
        return Point2((xs[idx], ys[idx]))