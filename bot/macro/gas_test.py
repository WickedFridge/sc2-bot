from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

if TYPE_CHECKING:
    from bot.macro.bunker_mining import BunkerMining
    from bot.macro.expansion import Expansion
    from bot.superbot import Superbot

GAS_TEST_COMMAND: str = 'GAS_TEST'
# regular mining reference (3 workers / refinery) measured on TorchesAIE_v4: ~160-164 vespene / min / refinery
# set to True to measure it again (regular -> bunker -> regular), False for the bunker phase only
INCLUDE_REGULAR_PHASES: bool = False
GAME_LOOPS_PER_SECOND: float = 22.4
# not measured: the workers settle in the new mining mode
WARMUP_LOOPS: int = round(30 * GAME_LOOPS_PER_SECOND)
MEASURE_LOOPS: int = round(120 * GAME_LOOPS_PER_SECOND)
VESPENE_PER_TRIP: int = 4
# a worker that stops carrying vespene that close to a townhall's edge just delivered it
DELIVERY_DISTANCE: float = 1.5


class GasMetrics:
    """Counts the vespene deliveries of each refinery (regular or bunker mined)"""
    bot: Superbot
    # last known carrying state of each worker (invisible workers keep theirs: in a bunker or a refinery)
    _was_carrying: Dict[int, bool]
    # last refinery each worker gathered
    _last_refinery: Dict[int, int]
    # game loops of the deliveries, by refinery tag
    deliveries: Dict[int, List[int]]

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.reset()

    def reset(self) -> None:
        self._was_carrying = {}
        self._last_refinery = {}
        self.deliveries = {}

    def update(self) -> None:
        game_loop: int = self.bot.state.game_loop
        refinery_tags: set[int] = self.bot.gas_buildings.tags
        townhalls: Units = self.bot.townhalls.ready
        for worker in self.bot.workers:
            if (worker.order_target in refinery_tags):
                self._last_refinery[worker.tag] = worker.order_target
            is_carrying: bool = worker.is_carrying_vespene
            if (
                self._was_carrying.get(worker.tag, False)
                and not is_carrying
                and worker.tag in self._last_refinery
                and townhalls.amount >= 1
            ):
                townhall: Unit = townhalls.closest_to(worker)
                if (worker.distance_to(townhall) <= townhall.radius + worker.radius + DELIVERY_DISTANCE):
                    self.deliveries.setdefault(self._last_refinery[worker.tag], []).append(game_loop)
            self._was_carrying[worker.tag] = is_carrying

    def vespene_per_minute(self, refinery_tag: int, start_loop: int, end_loop: int) -> float:
        trips: int = sum(1 for loop in self.deliveries.get(refinery_tag, []) if start_loop <= loop < end_loop)
        minutes: float = (end_loop - start_loop) / GAME_LOOPS_PER_SECOND / 60
        return trips * VESPENE_PER_TRIP / minutes if minutes > 0 else 0


@dataclass
class GasTestPhase:
    name: str
    bunker_mining: bool
    workers_per_refinery: int
    start_loop: int = 0
    # vespene per minute by refinery tag, filled at the end of the phase
    results: Dict[int, float] = field(default_factory=dict)


class GasTest:
    """
    Compares regular and bunker mining on the same refineries, on every base that can bunker mine.
    Started by the GAS_TEST chat command once the refineries and the mining bunkers are ready.
    Bunker mining phase only (2 workers / refinery), or with INCLUDE_REGULAR_PHASES:
    regular (3 workers / refinery, bunkers salvaged) -> bunker mining (bunkers created back) -> regular again.
    Each phase: WARMUP_LOOPS not measured, then MEASURE_LOOPS measured. Gas distribution is suspended on the tested bases.
    """
    bot: Superbot
    bunker_mining: BunkerMining
    metrics: GasMetrics
    phases: List[GasTestPhase]
    phase_index: int
    # positions of the tested expansions, empty when no test is running
    test_positions: List[Point2]

    def __init__(self, bot: Superbot, bunker_mining: BunkerMining) -> None:
        self.bot = bot
        self.bunker_mining = bunker_mining
        self.metrics = GasMetrics(bot)
        self.phases = []
        self.phase_index = -1
        self.test_positions = []

    @property
    def is_running(self) -> bool:
        return len(self.test_positions) >= 1

    @property
    def current_phase(self) -> Optional[GasTestPhase]:
        return self.phases[self.phase_index] if 0 <= self.phase_index < len(self.phases) else None

    def is_test_expansion(self, expansion: Expansion) -> bool:
        return expansion.position in self.test_positions

    def is_test_refinery(self, refinery: Unit) -> bool:
        return any(refinery.distance_to(position) <= 10 for position in self.test_positions)

    @property
    def test_expansions(self) -> List[Expansion]:
        return [expansion for expansion in self.bot.expansions if self.is_test_expansion(expansion)]

    async def execute(self) -> None:
        if (not self.is_running):
            if (self._command_received()):
                await self._start()
            return
        phase: GasTestPhase = self.current_phase
        self.metrics.update()
        self._remove_bunkers_if_regular(phase)
        self._fill_refineries(phase)
        if (self.bot.state.game_loop >= phase.start_loop + WARMUP_LOOPS + MEASURE_LOOPS):
            self._end_phase(phase)
            if (self.phase_index + 1 < len(self.phases)):
                await self._start_phase(self.phase_index + 1)
            else:
                self._end_test()

    def _command_received(self) -> bool:
        return any(
            message.player_id == self.bot.player_id and message.message.strip().upper() == GAS_TEST_COMMAND
            for message in self.bot.state.chat
        )

    async def _start(self) -> None:
        # ready base, 2 ready refineries and a ready mining bunker
        expansions: List[Expansion] = self.bot.expansions.bunker_mining_ready.expansions
        if (len(expansions) == 0):
            print('[GasTest] no ready base with its 2 refineries and its mining bunker ready, test not started')
            return
        self.test_positions = [expansion.position for expansion in expansions]
        self.phases = (
            [
                GasTestPhase('regular', bunker_mining=False, workers_per_refinery=3),
                GasTestPhase('bunker', bunker_mining=True, workers_per_refinery=2),
                GasTestPhase('regular (2)', bunker_mining=False, workers_per_refinery=3),
            ]
            if INCLUDE_REGULAR_PHASES
            else [GasTestPhase('bunker', bunker_mining=True, workers_per_refinery=2)]
        )
        self.metrics.reset()
        print(f'[GasTest] start on {len(expansions)} bases: {[str(position) for position in self.test_positions]}')
        await self._start_phase(0)

    async def _start_phase(self, index: int) -> None:
        self.phase_index = index
        phase: GasTestPhase = self.phases[index]
        self._apply_phase(phase)
        if (phase.bunker_mining):
            # bunkers salvaged by a previous regular phase (full test only): created back complete on their slot
            missing_bunkers: List[list] = [
                [UnitTypeId.BUNKER, 1, expansion.bunker_mining_position, self.bot.player_id]
                for expansion in self.test_expansions
                if expansion.bunker_mining_unit is None
            ]
            # debug_create_unit refuses an empty list
            if (len(missing_bunkers) >= 1):
                await self.bot.client.debug_create_unit(missing_bunkers)

    def _apply_phase(self, phase: GasTestPhase) -> None:
        phase.start_loop = self.bot.state.game_loop
        # disabled: the trios are released (workers unloaded) and no mining bunker is requested
        self.bunker_mining.enabled = phase.bunker_mining
        print(f'[GasTest] phase "{phase.name}": {phase.workers_per_refinery} workers / refinery, warmup {WARMUP_LOOPS} loops, measure {MEASURE_LOOPS} loops')

    def _remove_bunkers_if_regular(self, phase: GasTestPhase) -> None:
        """Regular phases: the mining bunkers are salvaged once empty"""
        if (phase.bunker_mining):
            return
        for expansion in self.test_expansions:
            bunker: Optional[Unit] = expansion.bunker_mining_unit
            if (
                bunker is not None
                and bunker.is_ready
                and bunker.cargo_used == 0
                and not bunker.is_using_ability(AbilityId.SALVAGEEFFECT_SALVAGE)
            ):
                print(f'[GasTest] salvage mining bunker {bunker.tag}')
                bunker(AbilityId.SALVAGEEFFECT_SALVAGE)

    def _fill_refineries(self, phase: GasTestPhase) -> None:
        """
        Replaces the gas distribution on the tested bases: keeps the phase's amount of workers on each refinery.
        In bunker mining, the trios send their extra workers back to minerals themselves.
        """
        for expansion in self.test_expansions:
            for refinery in expansion.refineries:
                harvesters: int = self.bunker_mining.harvesters(refinery)
                if (harvesters < phase.workers_per_refinery):
                    free_workers: Units = expansion.mineral_workers.filter(lambda worker: not worker.is_carrying_minerals)
                    if (free_workers.amount >= 1):
                        free_workers.closest_to(refinery).gather(refinery)
                elif (harvesters > phase.workers_per_refinery and not phase.bunker_mining):
                    extra_workers: Units = self.bot.workers.filter(
                        lambda worker: worker.order_target == refinery.tag and not worker.is_carrying_vespene
                    )
                    if (extra_workers.amount >= 1 and expansion.mineral_fields.amount >= 1):
                        extra_workers.first.gather(expansion.mineral_fields.closest_to(extra_workers.first))

    def _end_phase(self, phase: GasTestPhase) -> None:
        measure_start: int = phase.start_loop + WARMUP_LOOPS
        measure_end: int = measure_start + MEASURE_LOOPS
        for expansion in self.test_expansions:
            for refinery in expansion.refineries:
                phase.results[refinery.tag] = self.metrics.vespene_per_minute(refinery.tag, measure_start, measure_end)
        print(f'[GasTest] phase "{phase.name}" done')

    def _end_test(self) -> None:
        print('[GasTest] ===== results (vespene per game minute) =====')
        print('[GasTest] base | phase | refinery A | refinery B | total | workers | per worker')
        for expansion in self.test_expansions:
            refinery_tags: List[int] = [refinery.tag for refinery in expansion.refineries]
            for phase in self.phases:
                values: List[float] = [phase.results.get(tag, 0) for tag in refinery_tags]
                total: float = sum(values)
                workers: int = phase.workers_per_refinery * len(refinery_tags)
                per_refinery: str = ' | '.join(f'{value:6.1f}' for value in values)
                print(
                    f'[GasTest] {expansion.position} | {phase.name:12} | {per_refinery} | '
                    f'{total:6.1f} | {workers} | {total / workers if workers else 0:5.1f}'
                )
        # back to normal
        self.bunker_mining.enabled = True
        self.test_positions = []
        self.phases = []
        self.phase_index = -1
