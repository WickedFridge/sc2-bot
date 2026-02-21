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

    # --- Path scoring constants ---
    # Weight applied to local minima (descent reward): lower = more reward for escaping danger
    LOCAL_MIN_WEIGHT: float = 0.5
    # Weight of the sum of contributions as a tiebreaker vs the dominant peak
    SECONDARY_CONTRIBUTIONS_WEIGHT: float = 0.001
    # Weight of the mean danger on valid tiles as a tiebreaker
    MEAN_DANGER_WEIGHT: float = 0.1
    # Penalty per ratio of invalid/out-of-bounds tiles (0.0 = no penalty, 1.0 = full danger unit)
    INVALID_TILE_PENALTY: float = 5.0
    
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
        values: np.ndarray = self.sample_danger(path)

        # Mask out blocked/invalid tiles
        valid_mask: np.ndarray = (values != 999.0) & (values != self.INVALID_TILE_VALUE)

        if (not valid_mask.any()):
            return float('inf')

        valid_values: np.ndarray = values[valid_mask]

        # --- Main score: directional peak logic ---
        score: float = self._compute_directional_score(valid_values, self.LOCAL_MIN_WEIGHT, self.SECONDARY_CONTRIBUTIONS_WEIGHT)

        # --- Tiebreaker 1: mean danger on valid tiles ---
        mean_danger: float = float(valid_values.mean())

        # --- Tiebreaker 2: ratio of invalid/out-of-bounds tiles ---
        invalid_ratio: float = float((~valid_mask).sum()) / len(values)

        return score + self.MEAN_DANGER_WEIGHT * mean_danger + self.INVALID_TILE_PENALTY * invalid_ratio


    @staticmethod
    def _compute_directional_score(
        values: np.ndarray,
        local_min_weight: float,
        secondary_weight: float,
    ) -> float:
        """
        Scores a path based on its danger profile:
        - Local maxima are penalized (heading into danger)
        - Local minima are rewarded with local_min_weight (escaping danger)
        - Final score is dominated by the worst peak, with sum of others as tiebreaker
        """
        if (len(values) <= 1):
            return float(values[0]) if (len(values) == 1) else 0.0

        diffs: np.ndarray = np.diff(values)

        nonzero_mask: np.ndarray = diffs != 0
        nonzero_diffs: np.ndarray = diffs[nonzero_mask]
        nonzero_indices: np.ndarray = np.where(nonzero_mask)[0]

        if (len(nonzero_diffs) == 0):
            return float(values[0])

        signs: np.ndarray = np.sign(nonzero_diffs).astype(np.int8)
        sign_changes: np.ndarray = np.where(np.diff(signs) != 0)[0]
        inflection_indices: np.ndarray = nonzero_indices[sign_changes] + 1
        inflection_values: np.ndarray = values[inflection_indices]

        preceding_signs: np.ndarray = signs[sign_changes]
        is_local_max: np.ndarray = preceding_signs > 0

        contributions: np.ndarray = np.where(
            is_local_max,
            inflection_values,
            inflection_values * local_min_weight
        )

        last_value: float = float(values[-1])
        final_direction: int = int(signs[-1])
        final_contribution: float = last_value if (final_direction > 0) else last_value * local_min_weight

        all_contributions: np.ndarray = np.append(contributions, final_contribution)

        return float(all_contributions.max()) + secondary_weight * float(all_contributions.sum())