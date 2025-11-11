from typing import Iterator, List, Optional
import numpy as np
from functools import lru_cache
from sc2.bot_ai import BotAI
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ...utils.unit_tags import tower_types, menacing

def center(points: List[Point2]) -> Optional[Point2]:
    length: int = points.__len__()
    if (length == 0):
        return None
    x: float = 0
    y: float = 0
    for point in points:
        x += point.x
        y += point.y
    return Point2((x / length, y / length))

class InfluenceMap:
    bot: BotAI
    map: np.ndarray[np.float32]
    
    def __init__(self, bot: BotAI, map: np.ndarray) -> None:
        self.bot = bot
        self.map = map

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


class DangerMap:
    ground: InfluenceMap
    air: InfluenceMap
    dynamic_block_grid: InfluenceMap
    wall_distance: np.ndarray
    FALLOFF_LEVELS: List[tuple[float, float]] = [
        (1.00, 1.0),   # inside range
        (0.50, 2.0),   # medium threat
        (0.25, 4.0),   # low threat
        (0.05, 8.0),   # very low threat
    ]

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
    
    def init_danger_map(self):
        self.ground = InfluenceMap(self.bot, self.bot.game_info.pathing_grid.data_numpy.astype(np.float32))
        self.air = self.init_empty_map()
        self.dynamic_block_grid = self.init_empty_map(bool)
        self.compute_wall_distance()

    def init_empty_map(self, dtype = np.float32) -> InfluenceMap:
        height, width = self.bot.game_info.pathing_grid.data_numpy.shape
        return InfluenceMap(self.bot, np.zeros((height, width), dtype=dtype))
    
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
        self.dynamic_block_grid.map[:] = False  # reset

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

            self.dynamic_block_grid.map[y1:y2, x1:x2] = True
    
    def update_map(self, position: Point2, radius: float, value: float, air: bool = False, min_radius: float = 0.0):
        ux: int = int(position.x)
        uy: int = int(position.y)
        height, width = self.ground.shape
        
        kernel = self.influence_kernel(radius)
        
        x1 = max(0, ux - radius)
        x2 = min(width, ux + radius + 1)
        y1 = max(0, uy - radius)
        y2 = min(height, uy + radius + 1)

        kx1 = x1 - (ux - radius)
        kx2 = kx1 + (x2 - x1)
        ky1 = y1 - (uy - radius)
        ky2 = ky1 + (y2 - y1)

        submap = self.air.map[y1:y2, x1:x2] if air else self.ground.map[y1:y2, x1:x2]
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
        self.ground.map[:] = 0
        self.air.map[:] = 0
        dangerous_enemy_units: Units = self.bot.enemy_units + self.bot.enemy_structures(tower_types)

        for unit in dangerous_enemy_units:
            unit_position: Point2 = unit.position.rounded
            ground_dps: float = unit.ground_dps
            ground_range: float = unit.ground_range
            
            # melee unit don't have exactly 0 range
            if (unit.can_attack_ground and ground_range == 0):
                ground_range = 1.5
            
            air_dps: float = unit.air_dps
            air_range: float = unit.air_range
            
            # TODO : handle menacing special units
            if (ground_dps == 0 and unit.type_id in menacing):
                ground_dps = 10
            
            move_speed: float = unit.real_speed
            minimum_range: float = 2 if unit.type_id == UnitTypeId.SIEGETANKSIEGED else 0

            for weight, ms_factor in self.FALLOFF_LEVELS:
                ground_radius = int(ground_range + move_speed * ms_factor)
                self.update_map(unit_position, ground_radius, ground_dps * weight, False, minimum_range)
                air_radius = int(air_range + move_speed * ms_factor)
                self.update_map(unit_position, air_radius, air_dps * weight, True, minimum_range)

        # === Effects and Exceptions
        # effect_data: dict[EffectId, dict[str, float | bool]] = {
        #     EffectId.PSISTORMPERSISTENT: {
        #         'radius': 2,
        #         'dps': 23.3,
        #         'ground': True,
        #         'air': True
        #     }
        # }
        
        for effect in self.bot.state.effects:
            match(effect.id):
                case EffectId.PSISTORMPERSISTENT:
                    radius: int = 2
                    dps: float = 23.3
                    self.update_map(center(effect.positions), radius, dps, False)
                    self.update_map(center(effect.positions), radius, dps, True)
                case EffectId.RAVAGERCORROSIVEBILECP:
                    # 60 is the amount of damage, not sure about dps here
                    radius: float = 1
                    dps: float = 60
                    self.update_map(center(effect.positions), radius, dps, False)
                    self.update_map(center(effect.positions), radius, dps, True)
                case EffectId.BLINDINGCLOUDCP:
                    # let's put 60 as "very dangerous"
                    radius: float = 2
                    dps: float = 60
                    self.update_map(center(effect.positions), radius, dps, False)
                    self.update_map(center(effect.positions), radius, dps, True)
                case EffectId.LURKERMP:
                    radius: float = 1
                    dps: float = 20
                    for position in effect.positions:
                        self.update_map(position, radius, dps, False)
        
        # === Wall Danger ===
        # Distance 0 → unpathable → 999
        # Distance 1 → dangerous * 0.5
        # Distance 2 → dangerous * 0.25
        # >2 → safe-ish
        self.ground.map += np.where(
            self.wall_distance == 0,
            999,  # totally blocked
            np.exp(-self.wall_distance * 0.75) * 5.0
        )

        # === Absolute blockers (buildings + cliffs) ===
        static_blocked = (self.bot.game_info.pathing_grid.data_numpy == 0)
        blocked = self.dynamic_block_grid.map | static_blocked

        self.ground.map[blocked] = 999

    def get_masked_values(
        self, pos: Point2 | Unit, radius: int = 5, air: bool = False
    ) -> tuple[int, int, np.ma.MaskedArray]:
        rounded: Point2 = pos.position.rounded
        x = int(rounded.x)
        y = int(rounded.y)

        # Map bounds
        h, w = self.ground.shape

        x1 = max(0, x - radius)
        x2 = min(w, x + radius + 1)
        y1 = max(0, y - radius)
        y2 = min(h, y + radius + 1)

        # Extract sub-map
        submap = self.air.map[y1:y2, x1:x2] if air else self.ground.map[y1:y2, x1:x2]

        # Mask only tiles within circular radius
        yy, xx = np.ogrid[y1:y2, x1:x2]
        dist_sq = (xx - x) ** 2 + (yy - y) ** 2
        circle_mask = dist_sq <= radius * radius

        # Valid tiles = inside circle AND not environment (999)
        valid_mask = circle_mask & (submap != 999)
        
        # Create masked array: mask=True means INVALID tile
        masked_values = np.ma.masked_array(submap, mask=~valid_mask)

        return x1, y1, masked_values
    
    def pick_tile(
        self,
        pos: Point2 | Unit,
        radius: float,
        air: bool,
        score_fn: callable,
        prefer_direction: Point2 | None = None,
    ):
        # Base position
        rounded_radius: int = round(radius)
        rounded: Point2 = pos.position.rounded
        x: int = int(rounded.x)
        y: int = int(rounded.y)

        # Get the masked window: returns x1, y1, masked_values
        x1, y1, masked_values = self.get_masked_values(rounded, rounded_radius, air)
    
        # Build candidate tiles (masked values auto-skip)
        ys, xs = np.where(~masked_values.mask)

        # Precompute direction vector if provided
        if (prefer_direction is not None):
            vec: Point2 = prefer_direction - pos
            length: float = (vec.x * vec.x + vec.y * vec.y) ** 0.5

            if (length < 1e-6):
                Dx = Dy = None
            else:
                Dx = vec.x / length
                Dy = vec.y / length
        else:
            Dx = Dy = None

        ys, xs = np.where(~masked_values.mask)

        best_point: Point2 | None = None
        best_score: float | None = None

        for iy, ix in zip(ys, xs):
            value: float = masked_values[iy, ix]
            px: int = x1 + ix
            py: int = y1 + iy

            dx: int = px - x
            dy: int = py - y

            if (Dx is not None):
                # 1. Forward/backward component
                towards: float = dx * Dx + dy * Dy  # dot product

                # 2. Perpendicular spreading component
                proj_x: float = towards * Dx
                proj_y: float = towards * Dy
                perp_x: float = dx - proj_x
                perp_y: float = dy - proj_y
                extend: float = (perp_x * perp_x + perp_y * perp_y) ** 0.5
            else:
                towards: float = 0.0
                extend: float = 0.0

            # Compute score
            score: float = score_fn(value, towards, extend)

            if (best_score is None or score > best_score):
                best_score = score
                best_point = Point2((px, py))

        return best_point

    def most_dangerous_point(self, pos: Point2 | Unit, radius: int = 5, air: bool = False):
        x1, y1, masked_values = self.get_masked_values(pos, radius, air)
        
        # Find safest (minimum danger)
        iy, ix = np.unravel_index(masked_values.argmax(), masked_values.shape)

        return Point2((x1 + ix, y1 + iy))
    
    def best_attacking_spot(self, unit: Unit, target: Unit) -> Point2:
        air: bool = target.is_flying
        radius: int = unit.radius + target.radius
        if (air):
            radius += unit.air_range
        else:
            radius += unit.ground_range

        return self.pick_tile(
            target.position,
            radius,
            air,
            score_fn=lambda value, towards, extend: (-value + extend / 2 + towards),
            prefer_direction=unit.position,
        )
    
    def safest_spot_around(self, unit: Unit) -> Point2:
        radius: int = round(unit.real_speed * 1.4)
        air: bool = unit.is_flying

        return self.pick_tile(
            unit.position,
            radius,
            air,
            score_fn=lambda value, towards, extend: (-value - extend),
            prefer_direction=None,
        )
    
    
    
    def safest_spot_towards(self, unit: Unit, direction: Point2 | Unit) -> Point2:
        radius: int = round(unit.real_speed * 1.4)
        air: bool = unit.is_flying

        return self.pick_tile(
            unit.position,
            radius,
            air,
            score_fn=lambda value, towards, extend: (-value + towards),
            prefer_direction=direction.position,
        )
    
    def safest_spot_away(self, unit: Unit, direction: Point2 | Unit) -> Point2:
        radius: int = round(unit.real_speed * 1.4)
        air: bool = unit.is_flying

        return self.pick_tile(
            unit.position,
            radius,
            air,
            score_fn=lambda value, towards, extend: (-value - towards),
            prefer_direction=direction.position,
        )