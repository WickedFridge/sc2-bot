import math
from typing import Iterator, Optional
import numpy as np
from sc2.bot_ai import BotAI
from sc2.position import Point2
from sc2.unit import Unit


class InfluenceMap:
    bot: BotAI
    map: np.ndarray[np.float32]
    
    def __init__(self, bot: BotAI, map: np.ndarray = None, dtype: type = np.float32) -> None:
        self.bot = bot
        if (map is not None):
            self.map = map
        else:
            height, width = self.bot.game_info.pathing_grid.data_numpy.shape
            self.map = np.zeros((height, width), dtype=dtype)

    def __getitem__(self, pos: Point2) -> float:
        new_pos: Point2 = pos.rounded
        height, width = self.shape
        
        if (not (0 <= new_pos.x < width and 0 <= new_pos.y < height)):
            print(f'Error: {pos} is out of range')
            return 0
        
        return self.map[new_pos.y][new_pos.x]

    def __setitem__(self, pos: Point2, value: float) -> None:
        new_pos: Point2 = pos.rounded
        self.map[new_pos.y][new_pos.x] = value

    def __iter__(self) -> Iterator[Point2]:
        return iter(self.map)
    
    @property
    def shape(self):
        return self.map.shape
    
    @property
    def inverted(self):
        return ~self.map
    
    def _region(
        self, pos: Point2, radius: float, exact_dist = True
    ) -> Optional[tuple[int, int, int, int, np.ndarray, np.ndarray, np.ndarray]]:
        """
        Returns all geometry needed for reading or writing influence maps.
        use exact_dist = True to get exact distance instead of squared distance

        Output:
            x1, y1, x2, y2 : int
                Bounding box in map coordinates (Python slicing: y1:y2, x1:x2).

            submap : np.ndarray
                View of the map inside the bounding box.

            dx, dy : np.ndarray
                Distance from center in each direction (same shape as submap).

            dist_sq : np.ndarray
                Squared distance to center for each tile.

            dist : np.ndarray (replaces dist_sq)
                Actual distance (uses sqrt) for callers that need true radius.
        """

        # exact float center
        cx: float = pos.x
        cy: float = pos.y

        height, width = self.shape

        # --- clamp center into map ---
        cx: float = float(min(max(cx, 0), width - 1))
        cy: float = float(min(max(cy, 0), height - 1))

        # integer bounding box
        x1: int = max(0, math.floor(cx - radius))
        x2: int = min(width,  math.ceil(cx + radius + 1))
        y1: int = max(0, math.floor(cy - radius))
        y2: int = min(height, math.ceil(cy + radius + 1))

        # Extract submap view
        submap: np.ndarray = self.map[y1:y2, x1:x2]

        # local grid
        local_h: int = y2 - y1
        local_w: int = x2 - x1
        yy, xx = np.ogrid[0:local_h, 0:local_w]

        # Convert local coordinates to world coordinates
        tile_x: np.ndarray = xx + x1
        tile_y: np.ndarray = yy + y1
        
        # Distances
        dx: np.ndarray = tile_x - cx
        dy: np.ndarray = tile_y - cy

        dist_array: np.ndarray = (
            dx * dx + dy * dy
            if exact_dist == False
            else np.sqrt(dx * dx + dy * dy)
        )

        return x1, y1, x2, y2, submap, dist_array
    
    def read_values(
        self, pos: Point2 | Unit, radius: int = 5,
    ) -> tuple[int, int, np.ma.MaskedArray]:
        
        x1, y1, _, _, submap, dist_sq = self._region(pos, radius, exact_dist=False)

        # Squared distance mask (FAST)
        radius_sq: float = radius * radius
        circle_mask: np.ndarray = dist_sq <= radius_sq

        # Valid tiles = inside circle AND not environment (999)
        valid_mask = circle_mask & (submap != 999)

        masked_values = np.ma.masked_array(submap, mask=~valid_mask)

        return x1, y1, masked_values
    
    def update(
        self,
        position: Point2,
        radius: float,
        value: float,
        min_radius: float = 0.0,
        density_alpha: float = 0.3,
    ):
        if (radius <= 0 or value == 0):
            return

        x1, y1, x2, y2, _, dist = self._region(position, radius, exact_dist=True)

        # Uniform density inside radius
        density: np.ndarray = (dist <= radius).astype(float)

        # Apply inner hole if needed
        if (min_radius > 0):
            density[dist <= min_radius] = 0.0

        # -------- 2) Center bonus (optional) --------
        # makes center moderately more dangerous because escaping takes longer
        with np.errstate(divide="ignore", invalid="ignore"):
            center_bonus: np.ndarray = 1.0 + density_alpha * np.clip(1.0 - dist / radius, 0.0, 1.0)

        # -------- 3) Combine --------
        delta: np.ndarray = value * density * center_bonus

        self.map[y1:y2, x1:x2] += delta