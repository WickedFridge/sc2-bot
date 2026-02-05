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
    
    def sample_danger(self, path: list[Point2]) -> np.ndarray:

        # Convert path to arrays
        xs = np.fromiter((p.x for p in path), dtype=np.float32)
        ys = np.fromiter((p.y for p in path), dtype=np.float32)

        # World → local
        lx = np.rint(xs).astype(np.int32) - self.x1
        ly = np.rint(ys).astype(np.int32) - self.y1

        h, w = self.map.shape

        # Bounds check
        in_bounds = (
            (lx >= 0) & (lx < w) &
            (ly >= 0) & (ly < h)
        )

        # Valid tiles
        valid = in_bounds.copy()
        valid[in_bounds] &= self.valid[ly[in_bounds], lx[in_bounds]]

        # Fill with INVALID
        values = np.full(len(path), self.INVALID_TILE_VALUE, dtype=np.float32)

        # Read map
        values[valid] = self.map[ly[valid], lx[valid]]

        return values

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
    
    # def evaluate_path(self, path: list[Point2]) -> float:

    #     values = self.sample_danger(path)

    #     # Remove invalid
    #     good = values[values < 900]

    #     if (len(good) == 0):
    #         return 999.0

    #     # Starting danger
    #     start = good[0]

    #     # Prefix minimum (escape)
    #     min_prefix = np.minimum.accumulate(good)

    #     # Rise after escape
    #     rises = good - min_prefix
    #     worst_rise = np.max(rises)

    #     # Early danger (discourage early spike)
    #     early = good[: self.early_window]
    #     early_peak = np.max(early)

    #     # Relief (how much we managed to drop)
    #     relief = start - np.min(good)

    #     score = (
    #         max(start, worst_rise)
    #         + self.peak_weight * early_peak
    #         - self.relief_weight * relief
    #     )

    #     return float(score)