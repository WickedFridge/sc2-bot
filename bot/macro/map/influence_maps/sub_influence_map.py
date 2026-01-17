from sc2.position import Point2
import numpy as np
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI

class SubInfluenceMap(InfluenceMap):
    """
    A read-only, windowed InfluenceMap for path-based evaluation.
    """
    x1: int
    y1: int
    valid: np.ndarray
    
    escape_threshold: float
    relief_weight: float
    early_window: int

    def __init__(
        self,
        bot: BotAI,
        masked_array: np.ma.MaskedArray,
        x1: int,
        y1: int,
        escape_threshold: float = 5.0,
        relief_weight: float = 0.7,
        early_window: int = 3,
    ):
        """
        masked_array: the masked window of danger values
        x1, y1: top-left coordinates in the world
        """
        self.bot = bot
        self.x1 = x1
        self.y1 = y1
        
        self.escape_threshold = escape_threshold
        self.relief_weight = relief_weight
        self.early_window = early_window

        # Convert masked array to full array with np.inf for masked tiles
        map_data = masked_array.filled(0.0).astype(np.float32)
        self.valid = ~masked_array.mask  # True = usable tile
        super().__init__(bot, map_data)


    def world_to_local(self, pos: Point2) -> Point2:
        lx = int(round(pos.x)) - self.x1
        ly = int(round(pos.y)) - self.y1

        return Point2((lx, ly))
    
    def is_valid_local(self, pos: Point2) -> bool:
        lx: float = pos.x
        ly: float = pos.y

        return (
            0 <= lx < self.map.shape[1]
            and 0 <= ly < self.map.shape[0]
            and self.valid[ly, lx]
        )