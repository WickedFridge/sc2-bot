import cProfile
import faulthandler
import io
import pstats
import sys
from time import perf_counter
from typing import Dict, Optional


class StepProfiler:
    """
    Lightweight per-step profiler.

    * mark(label) closes the current section and attributes the elapsed time to `label`.
    * end() prints a breakdown when the step exceeds `slow_threshold_ms`.
    * After a slow step, the next step is run under cProfile (at most once every
      `deep_profile_cooldown` steps) and the most expensive functions are printed,
      since slow steps usually come in streaks.
    * While a step is running, a faulthandler watchdog dumps the Python stack of every
      thread to stderr if the step takes longer than `hang_timeout_s` — that shows
      exactly where the bot is stuck even if the game gets killed afterwards.
    """

    def __init__(
        self,
        slow_threshold_ms: float = 100,
        hang_timeout_s: float = 5,
        deep_profile: bool = True,
        deep_profile_cooldown: int = 100,
        deep_profile_lines: int = 25,
    ) -> None:
        self.slow_threshold_ms: float = slow_threshold_ms
        self.hang_timeout_s: float = hang_timeout_s
        self.sections: Dict[str, float] = {}
        self.step_start: float = 0
        self.section_start: float = 0
        self.total_ms: float = 0
        self.watchdog_enabled: bool = True
        self.deep_profile: bool = deep_profile
        self.deep_profile_cooldown: int = deep_profile_cooldown
        self.deep_profile_lines: int = deep_profile_lines
        self.last_deep_profile_iteration: int = -deep_profile_cooldown
        self.profile_next_step: bool = False
        self.cprofile: Optional[cProfile.Profile] = None

    def start(self) -> None:
        self.sections = {}
        if (self.profile_next_step):
            self.profile_next_step = False
            self.cprofile = cProfile.Profile()
            self.cprofile.enable()
        self.step_start = perf_counter()
        self.section_start = self.step_start
        self._arm_watchdog()

    def mark(self, label: str) -> None:
        now: float = perf_counter()
        self.sections[label] = self.sections.get(label, 0) + (now - self.section_start) * 1000
        self.section_start = now

    def end(self, iteration: int, game_time: Optional[float] = None) -> float:
        self._disarm_watchdog()
        self.total_ms = (perf_counter() - self.step_start) * 1000
        time_info: str = f' at {game_time:.1f}s' if (game_time is not None) else ''

        if (self.cprofile is not None):
            self.cprofile.disable()
            self._print_deep_profile(iteration, time_info)
            self.cprofile = None
            self.last_deep_profile_iteration = iteration

        if (self.total_ms >= self.slow_threshold_ms):
            top_sections: str = ', '.join(
                f'{label}: {duration:.1f}'
                for label, duration in sorted(self.sections.items(), key=lambda item: item[1], reverse=True)[:6]
            )
            print(
                f'[StepProfiler] Slow step {iteration}{time_info}: {self.total_ms:.1f} ms ({top_sections})',
                flush=True,
            )
            if (
                self.deep_profile
                and iteration - self.last_deep_profile_iteration >= self.deep_profile_cooldown
            ):
                self.profile_next_step = True
        return self.total_ms

    def _print_deep_profile(self, iteration: int, time_info: str) -> None:
        if (self.cprofile is None):
            return
        stream: io.StringIO = io.StringIO()
        stats: pstats.Stats = pstats.Stats(self.cprofile, stream=stream)
        stream.write('--- sorted by own time ---\n')
        stats.sort_stats(pstats.SortKey.TIME).print_stats(self.deep_profile_lines)
        stream.write('--- sorted by cumulative time ---\n')
        stats.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(self.deep_profile_lines)
        print(
            f'[StepProfiler] cProfile of step {iteration}{time_info} '
            f'({self.total_ms:.1f} ms with profiling overhead):\n{stream.getvalue()}',
            flush=True,
        )

    def _arm_watchdog(self) -> None:
        if (not self.watchdog_enabled):
            return
        try:
            faulthandler.dump_traceback_later(self.hang_timeout_s, repeat=False, file=sys.stderr)
        except Exception as error:
            # stderr without a real file descriptor (some runners) — just disable the watchdog
            print(f'[StepProfiler] Watchdog disabled: {error}')
            self.watchdog_enabled = False

    def _disarm_watchdog(self) -> None:
        if (self.watchdog_enabled):
            faulthandler.cancel_dump_traceback_later()
