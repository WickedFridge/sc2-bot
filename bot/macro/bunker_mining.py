from __future__ import annotations
from dataclasses import dataclass, field
import enum
from typing import Dict, List, Optional, TYPE_CHECKING

from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

if TYPE_CHECKING:
    from bot.macro.expansion import Expansion
    from bot.superbot import Superbot

# with bunker mining, 2 workers are enough to saturate a refinery
WORKERS_PER_REFINERY: int = 2
# distance from the bunker's center of the unload points
EXIT_DISTANCE: float = 2.5
# a worker within that distance of the bunker's edge is "next to it": served first, waits where it is
CLOSE_MARGIN: float = 1.0
# distance from the bunker's edge of the waiting point (within CLOSE_MARGIN, so the worker stops there)
WAITING_MARGIN: float = 0.5
# a worker stuck in the same status for that long is reset (~8s)
STUCK_TIMEOUT: int = 180


class MiningStatus(enum.Enum):
    NOT_MINING           = "NOT_MINING"
    # between the CC and the bunker, no vespene
    READY_TO_MINE        = "READY_TO_MINE"
    # inside the bunker, no vespene (heading to the refinery)
    MINE_IN_BUNKER       = "MINE_IN_BUNKER"
    # between the bunker and the refinery, no vespene
    MINE_OUT_BUNKER      = "MINE_OUT_BUNKER"
    # between the bunker and the refinery, carrying vespene
    MINE_BACK            = "MINE_BACK"
    # inside the bunker, carrying vespene (heading to the CC)
    MINE_BACK_IN_BUNKER  = "MINE_BACK_IN_BUNKER"
    # between the bunker and the CC, carrying vespene
    MINE_BACK_OUT_BUNKER = "MINE_BACK_OUT_BUNKER"


class BunkerDirection(enum.Enum):
    # empty, and no worker on its way to load
    FREE     = "FREE"
    # passengers are heading to the refinery (MINE_IN_BUNKER)
    OUTBOUND = "OUTBOUND"
    # passengers are heading to the CC (MINE_BACK_IN_BUNKER)
    INBOUND  = "INBOUND"


@dataclass
class BunkerLock:
    """
    A bunker has a single unload point, so all its passengers must travel in the same direction.
    Shared by the (up to) 2 trios using the same bunker.
    """
    direction: BunkerDirection = BunkerDirection.FREE
    # workers ordered to load in the current direction, until they're unloaded
    reserved_tags: set[int] = field(default_factory=set)
    # unload (rally) points: between both refineries / townhall side
    outbound_point: Optional[Point2] = None
    inbound_point: Optional[Point2] = None


@dataclass
class BunkerMiningTrio:
    refinery_tag: int
    bunker_tag: int
    workers: Dict[int, MiningStatus] = field(default_factory=dict)
    # game loop of each worker's last status change (stuck detection)
    status_since: Dict[int, int] = field(default_factory=dict)

    def set_status(self, worker_tag: int, status: MiningStatus, game_loop: int) -> None:
        self.workers[worker_tag] = status
        self.status_since[worker_tag] = game_loop

    def remove(self, worker_tag: int) -> None:
        self.workers.pop(worker_tag, None)
        self.status_since.pop(worker_tag, None)


@dataclass
class LoadRequest:
    """A worker asking to cross the bunker this frame"""
    worker: Unit
    bunker: Unit
    lock: BunkerLock
    direction: BunkerDirection
    # game loop of the worker's last status change
    waiting_since: int


class BunkerMining:
    bot: Superbot
    trios: List[BunkerMiningTrio]
    locks: Dict[int, BunkerLock]
    enabled: bool
    # gathered while updating the workers, then served by priority
    _load_requests: List[LoadRequest]

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.trios = []
        self.locks = {}
        # disabled (e.g. by the gas test): every trio is released and no mining bunker is requested
        self.enabled = True
        self._load_requests = []

    async def execute(self) -> None:
        self._sync_trios()
        self._claim_workers()
        self._update_workers()
        self._drive_bunkers()

    def trios_of_bunker(self, bunker_tag: int) -> List[BunkerMiningTrio]:
        return [trio for trio in self.trios if trio.bunker_tag == bunker_tag]

    # ---- queries for the rest of the bot (distribute_workers, speed mining, expansions) ----

    def is_bunker_miner(self, worker_tag: int) -> bool:
        return any(worker_tag in trio.workers for trio in self.trios)

    def trio_of_refinery(self, refinery_tag: int) -> Optional[BunkerMiningTrio]:
        for trio in self.trios:
            if (trio.refinery_tag == refinery_tag):
                return trio
        return None

    def is_bunker_mined(self, refinery: Unit) -> bool:
        return self.trio_of_refinery(refinery.tag) is not None

    def is_expansion_bunker_mined(self, expansion: Expansion) -> bool:
        return any(self.is_bunker_mined(refinery) for refinery in expansion.refineries)

    def ideal_harvesters(self, refinery: Unit) -> int:
        return WORKERS_PER_REFINERY if self.is_bunker_mined(refinery) else refinery.ideal_harvesters

    def harvesters(self, refinery: Unit) -> int:
        """
        assigned_harvesters isn't reliable for bunker mined refineries (loaded workers aren't counted):
        count the trio's workers, plus the workers just sent to it that aren't claimed yet
        """
        trio: Optional[BunkerMiningTrio] = self.trio_of_refinery(refinery.tag)
        if (trio is None):
            return refinery.assigned_harvesters
        return len(trio.workers) + self._unclaimed_workers(refinery).amount

    def release_one(self, expansion: Expansion, mineral_field: Unit) -> bool:
        """Sends one visible bunker miner of the expansion to the mineral field (the non carrying ones first)"""
        refinery_tags: set[int] = expansion.refineries.tags
        candidates: List[Unit] = [
            worker
            for trio in self.trios if trio.refinery_tag in refinery_tags
            for worker in self.bot.workers.tags_in(trio.workers.keys())
        ]
        if (len(candidates) == 0):
            return False
        worker: Unit = min(candidates, key=lambda candidate: candidate.is_carrying_vespene)
        self._forget_worker(worker.tag)
        print(f'[BunkerMining] release worker {worker.tag} to minerals')
        worker.gather(mineral_field)
        return True

    # ---- workers management ----

    def _unclaimed_workers(self, refinery: Unit) -> Units:
        """Workers sent to gather the refinery by the regular worker management"""
        return self.bot.workers.filter(
            lambda worker: worker.order_target == refinery.tag and not self.is_bunker_miner(worker.tag)
        )

    def _forget_worker(self, worker_tag: int) -> None:
        for trio in self.trios:
            trio.remove(worker_tag)
        for lock in self.locks.values():
            lock.reserved_tags.discard(worker_tag)

    def _claim_workers(self) -> None:
        """
        distribute_workers sends workers to the refineries, the trios take them over from there.
        Extra workers (the refinery was mined the regular way with 3 workers) go back to minerals.
        """
        for trio in self.trios:
            refinery: Optional[Unit] = self.bot.gas_buildings.find_by_tag(trio.refinery_tag)
            if (refinery is None):
                continue
            bunker: Optional[Unit] = self.bot.structures.find_by_tag(trio.bunker_tag)
            if (bunker is None):
                continue
            for worker in self._unclaimed_workers(refinery):
                if (len(trio.workers) < WORKERS_PER_REFINERY):
                    status: MiningStatus = self._initial_status(worker, bunker, refinery)
                    print(f'[BunkerMining] claim worker {worker.tag} for refinery {trio.refinery_tag} ({status.value})')
                    trio.set_status(worker.tag, status, self.bot.state.game_loop)
                elif (not worker.is_carrying_vespene):
                    minerals: Units = self.bot.mineral_field.closer_than(12, refinery)
                    print(f'[BunkerMining] extra worker {worker.tag} on refinery {trio.refinery_tag}, back to minerals')
                    if (minerals.amount >= 1):
                        worker.gather(minerals.closest_to(worker))
                    else:
                        worker.stop()

    def _initial_status(self, worker: Unit, bunker: Unit, refinery: Unit) -> MiningStatus:
        # the bunker is between the townhall and the refinery: closer to the refinery than the bunker = refinery side
        refinery_side: bool = worker.distance_to(refinery) < bunker.distance_to(refinery)
        if (worker.is_carrying_vespene):
            return MiningStatus.MINE_BACK if refinery_side else MiningStatus.MINE_BACK_OUT_BUNKER
        return MiningStatus.MINE_OUT_BUNKER if refinery_side else MiningStatus.READY_TO_MINE

    # ---- state machine ----

    def _update_workers(self) -> None:
        for trio in self.trios:
            bunker: Optional[Unit] = self.bot.structures.find_by_tag(trio.bunker_tag)
            refinery: Optional[Unit] = self.bot.gas_buildings.find_by_tag(trio.refinery_tag)
            lock: Optional[BunkerLock] = self.locks.get(trio.bunker_tag)
            if (bunker is None or refinery is None or lock is None):
                continue
            for worker_tag in list(trio.workers):
                self._update_worker(trio, worker_tag, bunker, refinery, lock)
        self._resolve_load_requests()

    def _update_worker(self, trio: BunkerMiningTrio, worker_tag: int, bunker: Unit, refinery: Unit, lock: BunkerLock) -> None:
        game_loop: int = self.bot.state.game_loop
        # None when loaded in the bunker or inside the refinery
        worker: Optional[Unit] = self.bot.workers.find_by_tag(worker_tag)
        in_bunker: bool = worker_tag in bunker.passengers_tags

        # taken by another system (building, repairing, defending): let it go
        if (worker is not None and (worker.is_constructing_scv or worker.is_repairing or worker.is_attacking)):
            print(f'[BunkerMining] worker {worker_tag} used elsewhere, released')
            self._forget_worker(worker_tag)
            return

        status: MiningStatus = trio.workers[worker_tag]
        next_status: MiningStatus = self._next_status(status, worker, in_bunker)
        if (next_status != status):
            if (status in (MiningStatus.MINE_IN_BUNKER, MiningStatus.MINE_BACK_IN_BUNKER)):
                # unloaded: the bunker slot is free
                lock.reserved_tags.discard(worker_tag)
            trio.set_status(worker_tag, next_status, game_loop)
            status = next_status
        elif (worker is not None and game_loop - trio.status_since[worker_tag] > STUCK_TIMEOUT):
            reset_status: MiningStatus = self._initial_status(worker, bunker, refinery)
            print(f'[BunkerMining] worker {worker_tag} stuck in {status.value}, reset to {reset_status.value}')
            lock.reserved_tags.discard(worker_tag)
            trio.set_status(worker_tag, reset_status, game_loop)
            status = reset_status

        if (worker is not None):
            self._act(worker, status, bunker, refinery, lock, trio.status_since[worker_tag])

    def _next_status(self, status: MiningStatus, worker: Optional[Unit], in_bunker: bool) -> MiningStatus:
        visible: bool = worker is not None
        carrying: bool = visible and worker.is_carrying_vespene
        # neither visible nor loaded: inside the refinery, it will come out with vespene
        in_refinery: bool = not visible and not in_bunker
        match (status):
            case MiningStatus.READY_TO_MINE if in_bunker:
                return MiningStatus.MINE_IN_BUNKER
            # unloaded straight into the refinery (rallied on it) between two steps: never seen outside
            case MiningStatus.MINE_IN_BUNKER if in_refinery:
                return MiningStatus.MINE_BACK
            case MiningStatus.MINE_IN_BUNKER if visible:
                return MiningStatus.MINE_OUT_BUNKER
            case MiningStatus.MINE_OUT_BUNKER if carrying or in_refinery:
                return MiningStatus.MINE_BACK
            case MiningStatus.MINE_BACK if in_bunker:
                return MiningStatus.MINE_BACK_IN_BUNKER
            # safety: seen outside without vespene, it didn't actually harvest yet
            case MiningStatus.MINE_BACK if visible and not carrying:
                return MiningStatus.MINE_OUT_BUNKER
            case MiningStatus.MINE_BACK_IN_BUNKER if visible:
                return MiningStatus.MINE_BACK_OUT_BUNKER
            case MiningStatus.MINE_BACK_OUT_BUNKER if visible and not carrying:
                return MiningStatus.READY_TO_MINE
        return status

    def _act(self, worker: Unit, status: MiningStatus, bunker: Unit, refinery: Unit, lock: BunkerLock, waiting_since: int) -> None:
        """Orders are only given when the worker isn't already doing the right thing"""
        match (status):
            case MiningStatus.READY_TO_MINE:
                # loads are served by priority once every worker is updated
                self._load_requests.append(LoadRequest(worker, bunker, lock, BunkerDirection.OUTBOUND, waiting_since))
            case MiningStatus.MINE_OUT_BUNKER:
                if (worker.order_target != refinery.tag):
                    worker.gather(refinery)
            case MiningStatus.MINE_BACK:
                self._load_requests.append(LoadRequest(worker, bunker, lock, BunkerDirection.INBOUND, waiting_since))
            case MiningStatus.MINE_BACK_OUT_BUNKER:
                if (not worker.is_returning):
                    worker.return_resource()

    def _try_load(self, worker: Unit, bunker: Unit, lock: BunkerLock, direction: BunkerDirection) -> None:
        # already allowed in: only re-order if the order was lost
        if (worker.tag in lock.reserved_tags):
            if (not self._is_loading(bunker, worker)):
                self._load(bunker, worker)
            return
        # the bunker is free or going our way, and has room left
        if (
            lock.direction in (BunkerDirection.FREE, direction)
            and len(lock.reserved_tags) < bunker.cargo_max
        ):
            lock.direction = direction
            lock.reserved_tags.add(worker.tag)
            self._load(bunker, worker)
            return
        # the bunker is used the other way: wait where it is if already next to it,
        # otherwise on the bunker's edge on the worker's side (always reachable, no detour around the refinery)
        if (self._is_close_to_bunker(worker, bunker)):
            # cancel the automatic order (return cargo / gather) that would make it walk around the bunker
            if (not worker.is_idle):
                worker.stop()
            return
        waiting_point: Point2 = bunker.position.towards(worker.position, bunker.radius + worker.radius + WAITING_MARGIN)
        is_heading_to_waiting_point: bool = (
            isinstance(worker.order_target, Point2)
            and worker.order_target.distance_to(waiting_point) < 0.5
        )
        if (not is_heading_to_waiting_point):
            worker.move(waiting_point)

    def _is_close_to_bunker(self, worker: Unit, bunker: Unit) -> bool:
        return worker.distance_to(bunker) <= bunker.radius + worker.radius + CLOSE_MARGIN

    def _resolve_load_requests(self) -> None:
        """
        Serves the workers asking for the bunker by priority (instead of the trios' order), so that when
        the bunker frees up, a worker already waiting next to it goes before one that just dropped its vespene:
        - the workers next to the bunker first
        - then the one in its current status for the longest time
        """
        def priority(request: LoadRequest) -> tuple[bool, int]:
            return (not self._is_close_to_bunker(request.worker, request.bunker), request.waiting_since)

        for request in sorted(self._load_requests, key=priority):
            self._try_load(request.worker, request.bunker, request.lock, request.direction)
        self._load_requests = []

    def _is_loading(self, bunker: Unit, worker: Unit) -> bool:
        # worker side (smart on the bunker) or bunker side (load order on the worker)
        return worker.order_target == bunker.tag or any(
            order.ability.id == AbilityId.LOAD_BUNKER and order.target == worker.tag
            for order in bunker.orders
        )

    def _load(self, bunker: Unit, worker: Unit) -> None:
        if (bunker.health_percentage >= 1):
            # full health: smart can only load (no repair), and each worker carries its own order,
            # so loads don't wait behind each other in the bunker's queue
            worker.smart(bunker)
        else:
            # damaged: smart would repair, the bunker gives the order instead,
            # queued so that the current order (another worker's load, an unload) isn't cancelled
            bunker(AbilityId.LOAD_BUNKER, worker, queue=len(bunker.orders) >= 1)

    def _drive_bunkers(self) -> None:
        """Unloads the miners as soon as they're in, frees the bunker once empty"""
        for bunker_tag, lock in self.locks.items():
            bunker: Optional[Unit] = self.bot.structures.find_by_tag(bunker_tag)
            if (bunker is None):
                continue
            miners_inside: List[int] = [tag for tag in bunker.passengers_tags if self.is_bunker_miner(tag)]
            if (len(miners_inside) == 0):
                if (len(lock.reserved_tags) == 0):
                    lock.direction = BunkerDirection.FREE
                continue
            if (bunker.is_using_ability(AbilityId.UNLOADALL_BUNKER)):
                continue
            rally_target: Optional[Point2 | Unit] = self._rally_target(miners_inside, lock)
            if (rally_target is None):
                continue
            if (not self._is_rallied_to(bunker, rally_target)):
                bunker(AbilityId.RALLY_UNITS, rally_target)
            bunker(AbilityId.UNLOADALL_BUNKER)

    def _rally_target(self, miners_inside: List[int], lock: BunkerLock) -> Optional[Point2 | Unit]:
        """
        Inbound: townhall side unload point.
        Outbound: directly on the refinery when every passenger goes to the same one,
        between both refineries otherwise.
        """
        if (self._is_inbound(miners_inside)):
            return lock.inbound_point
        refinery_tags: set[int] = {
            trio.refinery_tag
            for trio in self.trios
            if any(tag in trio.workers for tag in miners_inside)
        }
        if (len(refinery_tags) == 1):
            refinery: Optional[Unit] = self.bot.gas_buildings.find_by_tag(next(iter(refinery_tags)))
            if (refinery is not None):
                return refinery
        return lock.outbound_point

    def _is_rallied_to(self, bunker: Unit, target: Point2 | Unit) -> bool:
        if (len(bunker.rally_targets) == 0):
            return False
        rally = bunker.rally_targets[0]
        if (isinstance(target, Unit)):
            return rally.tag == target.tag
        return rally.tag is None and rally.point.distance_to(target) <= 0.5

    def _is_inbound(self, worker_tags: List[int]) -> bool:
        """Direction of the passengers, from their status (the lock may have been reset meanwhile)"""
        return any(
            trio.workers.get(tag) == MiningStatus.MINE_BACK_IN_BUNKER
            for trio in self.trios
            for tag in worker_tags
        )

    def on_unit_destroyed(self, unit_tag: int) -> None:
        # dead workers are forgotten right away (an alive worker can be invisible: in a bunker or a refinery)
        # destroyed bunkers/refineries are handled by the next _sync_trios
        self._forget_worker(unit_tag)

    def _sync_trios(self) -> None:
        """One trio per refinery of each base that can bunker mine, one lock per bunker used by a trio"""
        active_pairs: Dict[int, int] = {}  # refinery tag -> bunker tag
        exit_points: Dict[int, tuple[Point2, Point2]] = {}  # bunker tag -> (outbound, inbound)
        # disabled: no active pair, every trio is released below
        ready_expansions: List[Expansion] = self.bot.expansions.bunker_mining_ready.expansions if self.enabled else []
        for expansion in ready_expansions:
            bunker: Optional[Unit] = expansion.bunker_mining_unit
            townhall: Optional[Unit] = expansion.cc
            if (bunker is None or townhall is None):
                continue
            for refinery in expansion.refineries:
                active_pairs[refinery.tag] = bunker.tag
            # both refineries are on the same side of the bunker: unload towards their center
            exit_points[bunker.tag] = (
                bunker.position.towards(expansion.refineries.center, EXIT_DISTANCE),
                bunker.position.towards(townhall.position, EXIT_DISTANCE),
            )

        # obsolete trios: refinery/bunker destroyed, refinery depleted, townhall lost...
        for trio in list(self.trios):
            if (active_pairs.get(trio.refinery_tag) != trio.bunker_tag):
                self._release_trio(trio)

        known_refinery_tags: set[int] = {trio.refinery_tag for trio in self.trios}
        for refinery_tag, bunker_tag in active_pairs.items():
            if (refinery_tag not in known_refinery_tags):
                print(f'[BunkerMining] new trio: refinery {refinery_tag} / bunker {bunker_tag}')
                self.trios.append(BunkerMiningTrio(refinery_tag, bunker_tag))

        used_bunker_tags: set[int] = {trio.bunker_tag for trio in self.trios}
        for bunker_tag in list(self.locks):
            if (bunker_tag not in used_bunker_tags):
                del self.locks[bunker_tag]
        for bunker_tag in used_bunker_tags:
            lock: BunkerLock = self.locks.setdefault(bunker_tag, BunkerLock())
            lock.outbound_point, lock.inbound_point = exit_points[bunker_tag]

    def _release_trio(self, trio: BunkerMiningTrio) -> None:
        """Gives the trio's workers back to the regular worker management"""
        print(f'[BunkerMining] release trio: refinery {trio.refinery_tag} / bunker {trio.bunker_tag} ({len(trio.workers)} workers)')
        bunker: Optional[Unit] = self.bot.structures.find_by_tag(trio.bunker_tag)
        refinery: Optional[Unit] = self.bot.gas_buildings.find_by_tag(trio.refinery_tag)

        # loaded workers: unloaded next to the bunker, idle, distribute_workers picks them up
        if (bunker is not None and any(passenger.tag in trio.workers for passenger in bunker.passengers)):
            bunker(AbilityId.UNLOADALL_BUNKER)

        for worker_tag in trio.workers:
            worker: Optional[Unit] = self.bot.workers.find_by_tag(worker_tag)
            # not visible: loaded (unloaded above) or inside the refinery (keeps its regular gather cycle)
            if (worker is None):
                continue
            if (worker.is_carrying_vespene):
                worker.return_resource()
            elif (refinery is not None):
                worker.gather(refinery)
            else:
                worker.stop()
        self.trios.remove(trio)
