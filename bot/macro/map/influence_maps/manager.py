import numpy as np
from bot.macro.map.influence_maps.danger_map import DangerMap
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from bot.macro.map.influence_maps.layers.creep_layer import CreepLayer
from bot.macro.map.influence_maps.layers.effect_layer import EffectLayer
from bot.macro.map.influence_maps.layers.static_layer import StaticLayer
from sc2.bot_ai import BotAI
from sc2.position import Point2
from sc2.unit import Unit


class InfluenceMapManager:
    static: StaticLayer
    danger: DangerMap
    effects: EffectLayer
    creep: CreepLayer

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        
    
    def init_influence_maps(self):
        self.static = StaticLayer(self.bot)
        self.effects = EffectLayer(self.bot)
        # precompute wall_distance and dynamic block grid
        self.static.compute_wall_distance()
        self.static.update_dynamic_block_grid()
        self.creep = CreepLayer(self.bot)
        
        ground_map: np.ndarray = self.bot.game_info.pathing_grid.data_numpy.astype(np.float32)
        self.danger = DangerMap(self.bot, self.creep, map=ground_map)

    def update(self):
        # 1) static data (walls & blocks)
        self.static.update_dynamic_block_grid()
        self.creep.update()

        # 2) unit-based danger
        self.danger.update(include_structures=True)

        # 3) apply wall & block effects (danger depends on wall/block)
        self.danger.apply_wall_and_blocking(self.static.wall_distance, self.static.dynamic_block_grid.map)

        # 4) effects
        self.effects.update()
    
    # ---- Query helpers ----
    def read_values(self, pos: Point2, radius: float, air: bool = False, danger: bool = True, effects: bool = True):
        """
        Return x1,y1, masked_values from the combined map for reading/picking.
        """
        height, width = self.bot.game_info.pathing_grid.data_numpy.shape
        temporary_map: np.ndarray = np.zeros((height, width), dtype=np.float32)
        if (air):
            if (danger):
                temporary_map += self.danger.air.map
            if (effects):
                temporary_map += self.effects.air.map
        else:
            if (danger):
                temporary_map += self.danger.ground.map
            if (effects):
                temporary_map += self.effects.ground.map
        
        tmp: InfluenceMap = InfluenceMap(self.bot, temporary_map)
        return tmp.read_values(pos, radius)
    
    def pick_tile(
        self,
        pos: Point2 | Unit,
        radius: float,
        air: bool,
        score_fn: callable,
        prefer_direction: Point2 | None = None,
        danger: bool = True,
        effects: bool = True
    ) -> Point2:
        
        # Get the masked window: returns x1, y1, masked_values
        x1, y1, masked_values = self.read_values(pos, radius, air, danger, effects)

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

        # Base position
        # TODO why are we rounding here ?
        rounded: Point2 = pos.position.rounded
        x: int = int(rounded.x)
        y: int = int(rounded.y)
        
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
        x1, y1, masked_values = self.read_values(pos, radius, air, danger=True, effects=True)
        
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