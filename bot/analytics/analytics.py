from datetime import datetime, timezone
from typing import Dict, List
from bot.analytics.decisions import Decision, has_reacted, opening
from bot.analytics.match_history import MatchHistory
from bot.analytics.match_record import RESULT_CRASH, BuildUsage, CheeseDetection, MatchRecord
from bot.analytics.opponent_profile import OpponentProfile
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.matchup import Matchup
from sc2.data import Race, Result

MATCHUP_TO_RACE: Dict[Matchup, Race] = {
    Matchup.TvT: Race.Terran,
    Matchup.TvP: Race.Protoss,
    Matchup.TvZ: Race.Zerg,
    Matchup.TvR: Race.Random,
}


class Analytics:
    """
    Collects data about the current match and stores it in the match history.
    Analytics must never crash a game: every public method swallows its errors.
    """
    bot: Superbot
    history: MatchHistory
    record: MatchRecord | None

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.history = MatchHistory()
        self.record = None

    @property
    def source(self) -> str:
        return "ladder" if self.bot.is_ladder else "local"

    def start_match(self) -> None:
        try:
            self.recover_crashed_match()
            from bot.bot import VERSION
            self.record = MatchRecord(
                bot_version=VERSION,
                date=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                source=self.source,
                opponent_id=str(self.bot.opponent_id),
                opponent_race_requested=self.bot.enemy_race.name,
                opponent_race=MATCHUP_TO_RACE[self.bot.matchup].name,
                map=self.bot.game_info.map_name,
                matchup=self.bot.matchup.name,
                builds=[BuildUsage(self.bot.build_order.build.name.name, self.bot.time)],
                cheeses=[],
            )
            self.history.save_current(self.record)
        except Exception as e:
            print(f"[Analytics] start_match failed: {e}")

    def recover_crashed_match(self) -> None:
        # a match still pending means the previous game ended without on_end being called
        try:
            crashed: MatchRecord | None = self.history.pop_current()
            if (crashed is None):
                return
            crashed.result = RESULT_CRASH
            self.history.append(crashed)
            print(f"[Analytics] Recovered crashed match against {crashed.opponent_id}")
        except Exception as e:
            print(f"[Analytics] recover_crashed_match failed: {e}")

    def record_build_switch(self, build_name: str, time: float, trigger: str) -> None:
        if (self.record is None):
            return
        try:
            self.record.builds.append(BuildUsage(build_name, time, trigger))
            self.history.save_current(self.record)
        except Exception as e:
            print(f"[Analytics] record_build_switch failed: {e}")

    def record_situation(self) -> None:
        """Records each cheese the first time it's detected. Called every frame: no disk write unless a new cheese shows up."""
        situation: Situation = self.bot.scouting.situation
        if (self.record is None or self.record.cheeses is None or not situation.is_cheese):
            return
        if (any(cheese.name == situation.name for cheese in self.record.cheeses)):
            return
        try:
            self.record.cheeses.append(CheeseDetection(situation.name, round(self.bot.time, 1)))
            self.history.save_current(self.record)
        except Exception as e:
            print(f"[Analytics] record_situation failed: {e}")

    def opponent_profile(self) -> OpponentProfile:
        try:
            opponent_id: str = str(self.bot.opponent_id)
            matches: List[MatchRecord] = [
                match for match in self.history.load()
                if (match.source == self.source and match.opponent_id == opponent_id)
            ]
            profile: OpponentProfile = OpponentProfile.from_matches(matches)
            print(f"[Analytics] {profile} vs {opponent_id}")
            return profile
        except Exception as e:
            print(f"[Analytics] opponent_profile failed, assuming an unknown opponent: {e}")
            return OpponentProfile()

    def update_opponent_race(self, matchup: Matchup) -> None:
        if (self.record is None):
            return
        try:
            self.record.matchup = matchup.name
            self.record.opponent_race = MATCHUP_TO_RACE[matchup].name
            self.history.save_current(self.record)
        except Exception as e:
            print(f"[Analytics] update_opponent_race failed: {e}")

    def end_match(self, result: Result) -> None:
        if (self.record is None):
            return
        try:
            self.record.result = result.name
            self.record.duration = round(self.bot.time, 1)
            self.history.append(self.record)
            self.history.pop_current()
            self.record = None
        except Exception as e:
            print(f"[Analytics] end_match failed: {e}")

    async def announce_stats(self) -> None:
        try:
            for message in self.stats_messages():
                print(message)
                await self.bot.client.chat_send(message, False)
        except Exception as e:
            print(f"[Analytics] announce_stats failed: {e}")

    def stats_messages(self) -> List[str]:
        opponent_id: str = str(self.bot.opponent_id)
        matchup: Matchup = self.bot.matchup
        map_name: str = self.bot.game_info.map_name
        # builds that can't be selected in this matchup are not worth announcing
        playable_builds: List[str] = [build.name.name for build in self.bot.build_order.candidates(matchup)]
        openings: List[Decision] = []
        for match in self.history.load():
            decision: Decision | None = opening(match)
            if (
                decision is not None
                and decision.build in playable_builds
                and match.source == self.source
                and match.result in (Result.Victory.name, Result.Defeat.name)
                # random opponents: their race isn't known yet, so every matchup counts
                and (matchup == Matchup.TvR or match.matchup == matchup.name)
            ):
                openings.append(decision)
        opponent_openings: List[Decision] = [decision for decision in openings if decision.match.opponent_id == opponent_id]
        map_openings: List[Decision] = [
            decision for decision in openings
            if (decision.match.opponent_id != opponent_id and decision.match.map == map_name)
        ]
        if (len(opponent_openings) == 0 and len(map_openings) == 0):
            return ["Stats : no known match against this opponent or on this map"]

        opponent_scores: Dict[str, List[int]] = self.scores_by_build(opponent_openings)
        # an opening that only wins after a switch probably misses a scout: starting with the reaction may be better
        reacted_scores: Dict[str, List[int]] = self.scores_by_build(
            [decision for decision in opponent_openings if has_reacted(decision.match)]
        )
        map_scores: Dict[str, List[int]] = self.scores_by_build(map_openings)
        messages: List[str] = [
            f"Stats vs {opponent_id} ({matchup}) : W-L vs this opponent [of which after a switch] (W-L vs others on {map_name})"
        ]
        # builds played against this opponent first
        builds: List[str] = list(opponent_scores) + [build for build in map_scores if build not in opponent_scores]
        for build in builds:
            wins, losses = opponent_scores.get(build, [0, 0])
            reacted_wins, reacted_losses = reacted_scores.get(build, [0, 0])
            map_wins, map_losses = map_scores.get(build, [0, 0])
            messages.append(
                f"{self.display_name(build)} : {wins}-{losses} [{reacted_wins}-{reacted_losses}] ({map_wins}-{map_losses})"
            )
        return messages

    def scores_by_build(self, openings: List[Decision]) -> Dict[str, List[int]]:
        """[wins, losses] of each opening build"""
        scores: Dict[str, List[int]] = {}
        for decision in openings:
            score: List[int] = scores.setdefault(decision.build, [0, 0])
            score[0 if decision.match.result == Result.Victory.name else 1] += 1
        return scores

    def display_name(self, build: str) -> str:
        if (build in BuildOrderName.__members__):
            return BuildOrderName[build].value
        return build
