import faulthandler
import sys
from time import perf_counter
from typing import Dict, Optional


class StepProfiler:
    """
    Lightweight per-step profiler.

    * mark(label) closes the current section and attributes the elapsed time to `label`.
    * end() prints a breakdown when the step exceeds `slow_threshold_ms`.
    * While a step is running, a faulthandler watchdog dumps the Python stack of every
      thread to stderr if the step takes longer than `hang_timeout_s` — that shows
      exactly where the bot is stuck even if the game gets killed afterwards.
    """

    def __init__(self, slow_threshold_ms: float = 100, hang_timeout_s: float = 5) -> None:
        self.slow_threshold_ms: float = slow_threshold_ms
        self.hang_timeout_s: float = hang_timeout_s
        self.sections: Dict[str, float] = {}
        self.step_start: float = 0
        self.section_start: float = 0
        self.total_ms: float = 0
        self.watchdog_enabled: bool = True

    def start(self) -> None:
        self.sections = {}
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
        if (self.total_ms >= self.slow_threshold_ms):
            top_sections: str = ', '.join(
                f'{label}: {duration:.1f}'
                for label, duration in sorted(self.sections.items(), key=lambda item: item[1], reverse=True)[:6]
            )
            time_info: str = f' at {game_time:.1f}s' if (game_time is not None) else ''
            print(
                f'[StepProfiler] Slow step {iteration}{time_info}: {self.total_ms:.1f} ms ({top_sections})',
                flush=True,
            )
        return self.total_ms

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
