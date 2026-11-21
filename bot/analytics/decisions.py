"""
Reads the match history as a list of build decisions.
The history only stores facts (which builds were played, when and why): who deserves the credit for a result
is decided here, when reading, so it can evolve without migrating the stored matches.
Every decision made during a match is credited with the match result :
- the opening answers "which build to start with against this opponent, on this map"
  (a defensive build started from the beginning is an opening like any other)
- a reaction answers "which build to switch to, from this build, when this happens"
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from bot.analytics.match_record import TRIGGER_DEBUG, MatchRecord


@dataclass
class Decision:
    match: MatchRecord
    build: str
    time: float
    # build played before this decision, None for the opening
    previous_build: str | None = None
    # what made us switch: a Situation name. None for the opening, and for switches recorded before triggers existed
    trigger: str | None = None

    @property
    def is_opening(self) -> bool:
        return self.previous_build is None


def is_debug(match: MatchRecord) -> bool:
    """A build switched by hand: the match is a test, not choices made by the bot."""
    return any(build.trigger == TRIGGER_DEBUG for build in match.builds)


def match_decisions(match: MatchRecord) -> List[Decision]:
    if (is_debug(match)):
        return []
    decisions: List[Decision] = []
    previous_build: str | None = None
    for build in match.builds:
        decisions.append(Decision(match, build.name, build.start_time, previous_build, build.trigger))
        previous_build = build.name
    return decisions


def opening(match: MatchRecord) -> Decision | None:
    decisions: List[Decision] = match_decisions(match)
    return decisions[0] if decisions else None


def reactions(match: MatchRecord) -> List[Decision]:
    return match_decisions(match)[1:]


def has_reacted(match: MatchRecord) -> bool:
    return len(match.builds) > 1
