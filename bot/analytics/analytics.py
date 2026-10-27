from datetime import datetime, timezone
from typing import Dict, List
from bot.analytics.match_history import MatchHistory
from bot.analytics.match_record import RESULT_CRASH, BuildUsage, MatchRecord
from bot.strategy.build_order.bo_names import BuildOrderName
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
            )
            self.history.save_current(self.record)
        except Exception as e:
            print(f"[Analytics] start_match failed: {e}")

    def recover_crashed_match(self) -> None:
        # a match still pending means the previous game ended without on_end being called
        crashed: MatchRecord | None = self.history.pop_current()
        if (crashed is None):
            return
        crashed.result = RESULT_CRASH
        self.history.append(crashed)
        print(f"[Analytics] Recovered crashed match against {crashed.opponent_id}")

    def record_build_switch(self, build_name: str, time: float) -> None:
        if (self.record is None):
            return
        try:
            self.record.builds.append(BuildUsage(build_name, time))
            self.history.save_current(self.record)
        except Exception as e:
            print(f"[Analytics] record_build_switch failed: {e}")

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
        matches: List[MatchRecord] = [
            match for match in self.history.load()
            if (
                match.source == self.source
                and match.opponent_id == opponent_id
                # random opponents: their race isn't known yet, so every matchup counts
                and (matchup == Matchup.TvR or match.matchup == matchup.name)
            )
        ]
        if (len(matches) == 0):
            return ["Stats : aucun match connu contre cet adversaire"]

        results_by_build: Dict[str, Dict[str, int]] = {}
        for match in matches:
            build: str = match.starting_build or "Unknown"
            results: Dict[str, int] = results_by_build.setdefault(build, {})
            results[match.result] = results.get(match.result, 0) + 1

        messages: List[str] = [f"Stats vs {opponent_id} ({matchup}) : {len(matches)} matchs"]
        for build, results in results_by_build.items():
            score: str = (
                f"{results.get(Result.Victory.name, 0)}"
                f"-{results.get(Result.Defeat.name, 0)}"
            )
            if (results.get(Result.Tie.name, 0) > 0):
                score += f"-{results[Result.Tie.name]}T"
            messages.append(f"Stats {self.display_name(build)} : {score}")
        return messages

    def display_name(self, build: str) -> str:
        if (build in BuildOrderName.__members__):
            return BuildOrderName[build].value
        return build
