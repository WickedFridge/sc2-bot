import numpy as np
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId


class StaticLayer:
    """
    Computes static data:
     - wall_distance: distance to nearest unpathable tile (Manhattan BFS)
     - dynamic_block_grid: boolean InfluenceMap indicating blocked tiles (buildings)
    """
    bot: BotAI
    wall_distance: np.ndarray
    dynamic_block_grid: InfluenceMap

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.compute_wall_distance()
        self.dynamic_block_grid = InfluenceMap(bot, dtype=bool)
        
    def compute_wall_distance(self) -> np.ndarray:
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
    
    def update_dynamic_block_grid(self):
        """
        Fill dynamic_block_grid.map with True where current structures are blocking.
        Call every frame before layers that depend on block grid.
        """
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