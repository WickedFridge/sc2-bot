from __future__ import annotations
from typing import List, Set
from bot.analytics.match_record import MatchRecord
from bot.strategy.strategy_types import Situation


class OpponentProfile:
    """
    What the match history tells about the current opponent, built once at the start of the game.
    An unknown opponent may do anything: decisions based on this profile stay cautious when there's no data.
    """
    known: bool
    cheeses: Set[str]

    def __init__(self, known: bool = False, cheeses: Set[str] | None = None) -> None:
        self.known = known
        self.cheeses = cheeses or set()

    @staticmethod
    def from_matches(matches: List[MatchRecord]) -> OpponentProfile:
        # matches played before cheeses were tracked tell nothing about them
        tracked: List[MatchRecord] = [match for match in matches if match.cheeses is not None]
        cheeses: Set[str] = {cheese.name for match in tracked for cheese in (match.cheeses or [])}
        return OpponentProfile(known=len(tracked) > 0, cheeses=cheeses)

    def may_do(self, cheese: Situation) -> bool:
        return not self.known or cheese.name in self.cheeses

    def __repr__(self) -> str:
        if (not self.known):
            return "OpponentProfile(unknown)"
        return f"OpponentProfile(cheeses={sorted(self.cheeses)})"
