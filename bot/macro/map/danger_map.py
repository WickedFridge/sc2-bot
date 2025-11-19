import math
from typing import Iterator, List, Optional
import numpy as np
from functools import lru_cache
from bot.utils.point2_functions.utils import center
from sc2.bot_ai import BotAI
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ...utils.unit_tags import tower_types, menacing, friendly_fire

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
    exceptions: List[UnitTypeId] = [
        UnitTypeId.DISRUPTORPHASED
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
    
    def fix_exceptions(self, unit: Unit):
        print(f'range : {unit.ground_range}')
        print(f'dps : {unit.ground_dps}')
    
    def get_unit_property(self, unit: Unit) -> tuple[Point2, float, float, float, float, float, float]:
        position: Point2 = unit.position
        # health: float = unit.health + unit.shield
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
            case UnitTypeId.SIEGETANK:
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
            case UnitTypeId.CARRIER:
                # zone around carrier is dangerous
                ground_dps = 30
                ground_range = 12
                ground_dps = 30
                air_range = 12
            case _:
                pass

        return (
            position,
            # health,
            ground_dps,
            ground_range,
            air_dps,
            air_range,
            movement_speed,
            minimum_range
        )
        
    
    def update_map(
        self,
        position: Point2,
        radius: float,
        dps: float,
        air: bool = False,
        min_radius: float = 0.0,
        density_alpha: float = 0.3,
    ):
        # exact float center
        cx: float = position.x
        cy: float = position.y

        height, width = self.ground.shape
        submap: np.ndarray = self.air.map if air else self.ground.map

        if (radius <= 0):
            return

        # decide integer grid cells to consider (cell centers at integer (x,y) coordinates)
        x_min: int = math.floor(cx - radius)
        x_max: int = math.ceil(cx + radius)   # inclusive range end
        y_min: int = math.floor(cy - radius)
        y_max: int = math.ceil(cy + radius)   # inclusive range end

        # clip to map bounds
        x_min_clipped: int = max(0, x_min)
        x_max_clipped: int = min(width - 1, x_max)
        y_min_clipped: int = max(0, y_min)
        y_max_clipped: int = min(height - 1, y_max)

        if (x_max_clipped < x_min_clipped or y_max_clipped < y_min_clipped):
            return

        xs = np.arange(x_min_clipped, x_max_clipped + 1)
        ys = np.arange(y_min_clipped, y_max_clipped + 1)

        # meshgrid of integer cell coordinates
        YY, XX = np.meshgrid(ys, xs, indexing="ij")  # shape (Ny, Nx) matching sub-slices
        
        # distances from exact position to each cell center
        dx = XX.astype(float) - cx
        dy = YY.astype(float) - cy
        dist = np.sqrt(dx * dx + dy * dy)

        # -------- 1) Uniform density inside radius --------
        density: float = (dist <= radius).astype(float)

        # Apply inner hole if needed
        if (min_radius > 0):
            density[dist <= min_radius] = 0.0

        # -------- 2) Center bonus (optional) --------
        # makes center moderately more dangerous because escaping takes longer
        with np.errstate(divide="ignore", invalid="ignore"):
            center_bonus: np.ndarray = 1.0 + density_alpha * np.clip(1.0 - dist / radius, 0.0, 1.0)

        # -------- 3) Combine --------
        delta: np.ndarray = dps * density * center_bonus

        submap[y_min_clipped : y_max_clipped + 1, x_min_clipped : x_max_clipped + 1] += delta
        
    def update(self):
        # Reset to zeros
        self.ground.map[:] = 0
        self.air.map[:] = 0
        dangerous_enemy_units: Units = self.bot.enemy_units + self.bot.enemy_structures(tower_types)
        
        for unit in dangerous_enemy_units:
            (
                unit_position,
                ground_dps,
                ground_range,
                air_dps,
                air_range,
                move_speed,
                minimum_range,
            ) = self.get_unit_property(unit)
            
            
            # TODO : handle menacing special units
            if (ground_dps == 0 and unit.type_id in menacing):
                ground_dps = 15
                            
            move_speed: float = unit.real_speed
            minimum_range: float = 2 if unit.type_id == UnitTypeId.SIEGETANKSIEGED else 0
            # normalize with a smaller ratio

            for weight, ms_factor in self.FALLOFF_LEVELS:
                ground_radius = ground_range + move_speed * ms_factor
                self.update_map(unit_position, ground_radius, ground_dps * weight, False, minimum_range)
                air_radius = air_range + move_speed * ms_factor
                self.update_map(unit_position, air_radius, air_dps * weight, True, minimum_range)

        # === Effects and Exceptions
        for effect in self.bot.state.effects:
            effect_center: Point2 = (
                effect.positions.pop()
                if (len(effect.positions) == 1)
                else center(effect.positions)
            )
                
            match(effect.id):
                case "KD8CHARGE":
                    # KD8 does only 5 damage but let's estimate knockoff as 15
                    radius: int = 1
                    dps: float = 20
                    self.update_map(effect_center, radius, dps, False)
                case EffectId.PSISTORMPERSISTENT:
                    radius: int = 2
                    dps: float = 23.3
                    self.update_map(effect_center, radius, dps, False)
                    self.update_map(effect_center, radius, dps, True)
                case EffectId.RAVAGERCORROSIVEBILECP:
                    # 60 is the amount of damage, not sure about dps here
                    radius: float = 1
                    dps: float = 60
                    self.update_map(effect_center, radius, dps, False)
                    self.update_map(effect_center, radius, dps, True)
                case EffectId.BLINDINGCLOUDCP:
                    # let's put 30 as "very dangerous"
                    radius: int = 2
                    dps: float = 30
                    self.update_map(effect_center, radius, dps, False)
                    self.update_map(effect_center, radius, dps, True)
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
    ) -> Point2:
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

        if (best_point is None):
            print("Error - no best point found")
            return prefer_direction or pos
        return best_point

    def most_dangerous_point(self, pos: Point2 | Unit, radius: int = 5, air: bool = False):
        x1, y1, masked_values = self.get_masked_values(pos, radius, air)
        
        # Find safest (minimum danger)
        iy, ix = np.unravel_index(masked_values.argmax(), masked_values.shape)

        return Point2((x1 + ix, y1 + iy))
    
    def best_attacking_spot(self, unit: Unit, target: Unit, risk: float = 0.7) -> Point2:
        target_air: bool = target.is_flying
        distance: float = unit.radius + target.radius
        if (target_air):
            distance += unit.air_range
        else:
            distance += unit.ground_range
        
        target_range: float = unit.radius + target.radius
        if (unit.is_flying):
            target_range += target.air_range
        else:
            target_range += target.ground_range
        
        escape_range: float = target.real_speed * 1.4
        distance -= escape_range * risk

        # we want to be in range, but not too close from melee unit, but still out of range of ranged units
        ideal_range: float = min(target_range + 2, distance)
        range_bias: float = -(abs(distance - ideal_range))
        weight_t: float = 1.0
        weight_r: float = 0.8

        return self.pick_tile(
            target.position,
            distance,
            target_air,
            score_fn=lambda value, towards, extend: (-value + extend / 2 + towards * weight_t + range_bias * weight_r),
            prefer_direction=unit.position,
        )
    
    def safest_spot_around_point(self, spot: Point2, radius: float = 4, air: bool = False) -> Point2:
        return self.pick_tile(
            spot,
            radius,
            air,
            score_fn=lambda value, towards, extend: (-value - extend),
            prefer_direction=None,
        )
    
    def safest_spot_around_unit(self, unit: Unit) -> Point2:
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
    
    def safest_spot_away(self, unit: Unit, direction: Point2 | Unit, range_modifier: float = 1) -> Point2:
        radius: int = max(2, round(unit.real_speed * 1.4 * range_modifier))
        air: bool = unit.is_flying

        return self.pick_tile(
            unit.position,
            radius,
            air,
            score_fn=lambda value, towards, extend: (-value - 2 * towards + extend),
            prefer_direction=direction.position,
        )