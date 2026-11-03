from __future__ import annotations
from dataclasses import dataclass
import math
import random
from typing import TYPE_CHECKING, Dict, List, Type
from bot.analytics.match_history import MatchHistory
from bot.analytics.match_record import RESULT_CRASH, MatchRecord
from bot.utils.matchup import Matchup
from sc2.data import Result

if TYPE_CHECKING:
    from bot.strategy.build_order.build_order import BuildOrder

# how much a past game tells about the current one, by (same opponent, same map)
SIMILARITY: Dict[tuple[bool, bool], float] = {
    (True, True): 1.0,
    (True, False): 0.85,
    (False, True): 0.5,
    (False, False): 0.2,
}
# each older game against the opponent weighs DECAY times the next more recent one,
# so the selection adapts when the opponent changes and old builds get re-explored
DECAY: float = 0.98
# max total weight (in games) that other opponents can bring to a build,
# so that a large history against other bots doesn't drown the games against this one
OTHER_OPPONENTS_MAX_WEIGHT: float = 5.0
# when a build's winrate on this map differs from its winrate on other maps, the games on other maps count less :
# their weight is multiplied by exp(-confidence * (gap / MAP_GAP_SCALE)²), so small gaps barely matter
MAP_GAP_SCALE: float = 0.3
# number of (weighted) games on the map needed to trust half of the gap
MAP_CONFIDENCE_GAMES: float = 3.0


@dataclass
class BuildScore:
    wins: float = 0.0
    games: float = 0.0

    def add(self, score: float, weight: float) -> None:
        self.wins += score * weight
        self.games += weight

    @property
    def losses(self) -> float:
        return self.games - self.wins

    @property
    def winrate(self) -> float:
        # Laplace smoothing : an unknown build is assumed to be 50%
        return (self.wins + 1) / (self.games + 2)

    def __add__(self, other: BuildScore) -> BuildScore:
        return BuildScore(self.wins + other.wins, self.games + other.games)

    def scaled(self, ratio: float) -> BuildScore:
        return BuildScore(self.wins * ratio, self.games * ratio)

    def capped(self, max_games: float) -> BuildScore:
        if (self.games <= max_games):
            return self
        return self.scaled(max_games / self.games)


class BuildSelector:
    """
    Picks the starting build with Thompson sampling over the match history.
    Every past game counts for its similarity with the current one (opponent, map).
    Each build's winrate is modeled by a Beta distribution over these weighted games :
    uncertain builds sometimes draw a high sample (exploration),
    and as games are played the best build ends up drawing the highest sample almost every time (convergence).
    """
    history: MatchHistory
    source: str

    def __init__(self, history: MatchHistory, source: str) -> None:
        self.history = history
        self.source = source

    def select(
        self,
        candidates: List[Type[BuildOrder]],
        opponent_id: str,
        matchup: Matchup,
        map_name: str,
    ) -> Type[BuildOrder]:
        names: List[str] = [candidate.name.name for candidate in candidates]
        matches: List[MatchRecord] = [
            match for match in self.history.load()
            if (
                match.source == self.source
                and match.matchup == matchup.name
                and match.starting_build in names
                and self.match_score(match) is not None
            )
        ]
        # weighted scores of each build, by (same opponent, same map)
        scores: Dict[str, Dict[tuple[bool, bool], BuildScore]] = {
            name: {key: BuildScore() for key in SIMILARITY} for name in names
        }
        recency: float = 1.0
        # the history is appended chronologically : most recent matches are last
        for match in reversed(matches):
            score: float | None = self.match_score(match)
            assert match.starting_build is not None and score is not None
            key: tuple[bool, bool] = (match.opponent_id == opponent_id, match.map == map_name)
            weight: float = SIMILARITY[key]
            if (key[0]):
                weight *= recency
                recency *= DECAY
            scores[match.starting_build][key].add(score, weight)

        print(f"[BuildSelector] {matchup.name} vs {opponent_id} on {map_name}")
        best_candidate: Type[BuildOrder] = candidates[0]
        best_sample: float = -1
        for candidate, name in zip(candidates, names):
            build_scores: Dict[tuple[bool, bool], BuildScore] = scores[name]
            map_factor: float = self.map_factor(build_scores)
            opponent: BuildScore = build_scores[(True, True)] + build_scores[(True, False)].scaled(map_factor)
            others: BuildScore = (
                build_scores[(False, True)] + build_scores[(False, False)].scaled(map_factor)
            ).capped(OTHER_OPPONENTS_MAX_WEIGHT)
            alpha: float = 1 + opponent.wins + others.wins
            beta: float = 1 + opponent.losses + others.losses
            sample: float = random.betavariate(alpha, beta)
            print(
                f"[BuildSelector]   {candidate.name.value} : "
                f"vs opponent {opponent.wins:.1f}/{opponent.games:.1f}, "
                f"vs others {others.wins:.1f}/{others.games:.1f}, "
                f"other maps x{map_factor:.2f}, "
                f"expected {alpha / (alpha + beta):.0%}, sample {sample:.2f}"
            )
            if (sample > best_sample):
                best_sample = sample
                best_candidate = candidate
        print(f"[BuildSelector] Selected {best_candidate.name.value}")
        return best_candidate

    def map_factor(self, build_scores: Dict[tuple[bool, bool], BuildScore]) -> float:
        """
        How much the games on other maps still count for this build, between 0 and 1.
        It decreases smoothly as the winrate on this map gets far from the winrate on other maps,
        the more games on this map back that gap.
        """
        on_map: BuildScore = build_scores[(True, True)] + build_scores[(False, True)]
        other_maps: BuildScore = build_scores[(True, False)] + build_scores[(False, False)]
        gap: float = on_map.winrate - other_maps.winrate
        confidence: float = on_map.games / (on_map.games + MAP_CONFIDENCE_GAMES)
        return math.exp(-confidence * (gap / MAP_GAP_SCALE) ** 2)

    def match_score(self, match: MatchRecord) -> float | None:
        if (match.result == Result.Victory.name):
            return 1.0
        if (match.result == Result.Defeat.name):
            return 0.0
        if (match.result == Result.Tie.name):
            return 0.5
        # a crash on the ladder is a lost game, locally it's usually a game we killed ourselves
        if (match.result == RESULT_CRASH and self.source == "ladder"):
            return 0.0
        return None
