from typing import Iterator, List
import numpy as np
from functools import lru_cache
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ...utils.unit_tags import tower_types, menacing


class DangerMap:
    map: np.ndarray[np.float32]
    dynamic_block_grid: np.ndarray[bool]
    wall_distance: np.ndarray
    FALLOFF_LEVELS: List[tuple[float, float]] = [
        (1.00, 1.0),   # inside range
        (0.50, 2.0),   # medium threat
        (0.25, 4.0),   # low threat
        (0.05, 8.0),   # very low threat
    ]

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot

    def __getitem__(self, pos: Point2) -> float:
        new_pos: Point2 = pos.rounded
        height, width = self.map.shape
        
        if (not (0 <= new_pos.x < width and 0 <= new_pos.y < height)):
            print(f'Error: {pos} is out of range')
            return 0
        
        return self.map[new_pos.y][new_pos.x]

    def __setitem__(self, pos: Point2, value: float) -> None:
        new_pos: Point2 = pos.rounded
        self.map[new_pos.y][new_pos.x] = value

    def __iter__(self) -> Iterator[Point2]:
        return iter(self.map)
    
    def init_danger_map(self):
        self.map = self.bot.game_info.pathing_grid.data_numpy.astype(np.float32)
        self.init_dynamic_block_grid()
        self.compute_wall_distance()

    def init_dynamic_block_grid(self):
        height, width = self.bot.game_info.pathing_grid.data_numpy.shape
        self.dynamic_block_grid: np.ndarray[bool] = np.zeros((height, width), dtype=bool)
    
    def compute_wall_distance(self):
        """
        Compute distance from each tile to nearest unpathable tile.
        """
        pathing: np.ndarray = self.bot.game_info.pathing_grid.data_numpy
        wall_mask: np.ndarray = (pathing == 0)

        # Distance transform (cheap even for 200x200)
        dist: np.ndarray = np.full_like(pathing, fill_value=9999, dtype=np.float32)

        # Unpathable tiles = distance 0
        dist[wall_mask] = 0

        # BFS expansion (Manhattan distance, good enough)
        # 4-neighborhood offsets
        offsets = [(1,0), (-1,0), (0,1), (0,-1)]

        queue = list(zip(*np.where(wall_mask)))

        idx = 0
        while idx < len(queue):
            y, x = queue[idx]
            idx += 1

            d = dist[y, x] + 1

            for dy, dx in offsets:
                ny, nx = y + dy, x + dx
                if 0 <= ny < dist.shape[0] and 0 <= nx < dist.shape[1]:
                    if d < dist[ny, nx]:
                        dist[ny, nx] = d
                        queue.append((ny, nx))

        self.wall_distance = dist
    
    @lru_cache(maxsize = None)
    def influence_kernel(self, radius: int) -> np.ndarray:
        """Return a 2D boolean mask of points inside the circle."""
        y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
        mask = (x * x + y * y) <= (radius * radius)
        return mask
    
    def update_dynamic_block_grid(self):
        self.dynamic_block_grid[:] = False  # reset

        for structure in self.bot.structures.not_flying:
            if (structure.type_id == UnitTypeId.SUPPLYDEPOTLOWERED):
                continue
            radius = int(
                structure.footprint_radius
                if (
                    structure.footprint_radius is not None
                    and structure.footprint_radius > 0
                )
                else structure.radius
            )
            cx, cy = int(structure.position.x), int(structure.position.y)

            x1 = max(0, cx - radius)
            x2 = min(self.dynamic_block_grid.shape[1], cx + radius + 1)
            y1 = max(0, cy - radius)
            y2 = min(self.dynamic_block_grid.shape[0], cy + radius + 1)

            self.dynamic_block_grid[y1:y2, x1:x2] = True
    
    def update_map(self, position: Point2, radius: float, value: float, min_radius: float = 0.0):
        ux: int = int(position.x)
        uy: int = int(position.y)
        height, width = self.map.shape
        
        kernel = self.influence_kernel(radius)
        
        x1 = max(0, ux - radius)
        x2 = min(width, ux + radius + 1)
        y1 = max(0, uy - radius)
        y2 = min(height, uy + radius + 1)

        kx1 = x1 - (ux - radius)
        kx2 = kx1 + (x2 - x1)
        ky1 = y1 - (uy - radius)
        ky2 = ky1 + (y2 - y1)

        submap = self.map[y1:y2, x1:x2]
        subkernel = kernel[ky1:ky2, kx1:kx2]

        if (min_radius > 0):
            # Create a mask for the inner circle to exclude
            y_idx, x_idx = np.ogrid[-radius:radius+1, -radius:radius+1]
            inner_mask = (x_idx**2 + y_idx**2) <= (min_radius**2)
            inner_submask = inner_mask[ky1:ky2, kx1:kx2]
            
            # Remove inner area from kernel
            subkernel = subkernel & (~inner_submask)

        submap[subkernel] += value
        
    def update(self):
        # Reset to zeros
        self.map[:] = 0
        dangerous_enemy_units: Units = self.bot.enemy_units + self.bot.enemy_structures(tower_types)

        for unit in dangerous_enemy_units:
            if (not unit.can_attack_ground):
                continue

            dps: float = unit.ground_dps
            if (dps == 0 and unit.type_id in menacing):
                dps = 10
            base_range: float = unit.ground_range if unit.ground_range >= 2 else 2
            move_speed: float = unit.movement_speed
            minimum_range: float = 2 if unit.type_id == UnitTypeId.SIEGETANKSIEGED else 0

            unit_position: Point2 = unit.position.rounded
            
            for weight, ms_factor in self.FALLOFF_LEVELS:
                radius = int(base_range + move_speed * ms_factor)
                self.update_map(unit_position, radius, dps * weight, minimum_range)

        # === Wall Danger ===
        # Distance 0 → unpathable → 999
        # Distance 1 → dangerous * 0.5
        # Distance 2 → dangerous * 0.25
        # >2 → safe-ish
        self.map += np.where(
            self.wall_distance == 0,
            999,  # totally blocked
            np.exp(-self.wall_distance * 0.75) * 5.0
        )

        # === Absolute blockers (buildings + cliffs) ===
        static_blocked = (self.bot.game_info.pathing_grid.data_numpy == 0)
        blocked = self.dynamic_block_grid | static_blocked

        self.map[blocked] = 999

    def safest_point_near(self, pos: Point2 | Unit, radius: int = 5) -> Point2:
        rounded: Point2 = pos.position.rounded
        x = int(rounded.x)
        y = int(rounded.y)

        # Map bounds
        h, w = self.map.shape

        x1 = max(0, x - radius)
        x2 = min(w, x + radius + 1)
        y1 = max(0, y - radius)
        y2 = min(h, y + radius + 1)

        # Extract sub-map
        submap = self.map[y1:y2, x1:x2]

        # Mask only tiles within circular radius
        yy, xx = np.ogrid[y1:y2, x1:x2]
        dist_sq = (xx - x) ** 2 + (yy - y) ** 2
        circle_mask = dist_sq <= radius * radius

        # Apply mask
        masked_values = np.where(circle_mask, submap, float("inf"))

        # Find safest (minimum danger)
        iy, ix = np.unravel_index(masked_values.argmin(), masked_values.shape)

        return Point2((x1 + ix, y1 + iy))