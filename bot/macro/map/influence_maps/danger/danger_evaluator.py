from __future__ import annotations
import numpy as np
from bot.macro.map.influence_maps.sub_influence_map import SubInfluenceMap
from sc2.position import Point2

class DangerEvaluator(SubInfluenceMap):
    """
    Evaluates the danger along a path using a small InfluenceMap window.
    Only considers tiles inside the given masked array.
    """
    INVALID_TILE_VALUE: float = 10

    def sample_danger(self, path: list[Point2]) -> np.ndarray | None:
        values = []

        for point in path:
            local_pos: Point2 = self.world_to_local(point)

            if (not self.is_valid_local(local_pos)):
                values.append(self.INVALID_TILE_VALUE)
                continue
            
            lx = int(local_pos.x)
            ly = int(local_pos.y)
            value = self.map[ly, lx]
            
            values.append(value)

        return np.array(values, dtype=np.float32)
    
    @staticmethod
    def soft_max(values: np.ndarray, alpha: float = 0.1) -> float:
        # numerical stability
        v = values - values.max()
        return (np.log(np.exp(alpha * v).sum()) / alpha) + values.max()
    
    def evaluate_path(self, path: list[Point2]) -> float:
        values = self.sample_danger(path)
        current_peak = 0
        
        for i in range(0, len(values)):
            if (values[i] == 999.0):
                continue
            if (values[i] >= current_peak):
                current_peak = values[i]

        return current_peak