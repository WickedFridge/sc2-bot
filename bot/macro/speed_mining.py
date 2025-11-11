# Note : this file was copied from Sharpy's repo:
# https://github.com/DrInfy/sharpy-sc2/blob/develop/sharpy/plans/tactics/speed_mining.py

from typing import List, Dict

from bot.utils.sharpy_sc2math import get_intersections
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

MINING_RADIUS = 1.325


class SpeedMining:
    """Make worker mine faster perhaps?"""
    ai: BotAI

    def __init__(self, ai, enable_on_return=True, enable_on_mine=True) -> None:
        self.ai = ai
        self.enable_on_return = enable_on_return
        self.enable_on_mine = enable_on_mine
        self.mineral_target_dict: Dict[Point2, Point2] = {}

    async def start(self):
        self.calculate_expansion_locations()

    async def execute(self) -> bool:
        if (len(self.ai.townhalls) < 1 or (not self.enable_on_return and not self.enable_on_mine)):
            return True
        workers = self.get_mineral_workers()
        self.speedmine(workers)
        return True

    def get_mineral_workers(self) -> Units:
        def miner_filter(unit: Unit) -> bool:
            if (unit.is_carrying_vespene):
                return False
            if (unit.order_target is not None and isinstance(unit.order_target, int)):
                target_unit = self.ai.mineral_field.find_by_tag(unit.order_target)
                if (target_unit is not None and target_unit.has_vespene):
                    return False
            return True

        units = self.ai.workers.collecting.filter(miner_filter)

        return units

    def speedmine(self, workers: Units):
        for worker in workers:
            self.speedmine_single(worker)

    def speedmine_single(self, worker: Unit):
        townhall = self.ai.townhalls.closest_to(worker)

        if (self.enable_on_return and worker.is_returning and len(worker.orders) == 1):
            target: Point2 = townhall.position
            target = target.towards(worker, townhall.radius + worker.radius)
            if (0.75 < worker.distance_to(target) < 2):
                worker.move(target)
                worker(AbilityId.SMART, townhall, True)
                return

        if (
            self.enable_on_mine
            and not worker.is_returning
            and len(worker.orders) == 1
            and isinstance(worker.order_target, int)
        ):
            mf = self.ai.mineral_field.find_by_tag(worker.order_target)
            if (mf is not None and mf.is_mineral_field):

                target = self.mineral_target_dict.get(mf.position)
                if (target and 0.75 < worker.distance_to(target) < 2):
                    worker.move(target)
                    worker(AbilityId.SMART, mf, True)

    def calculate_expansion_locations(self):
        expansion_locations: List[Point2] = self.ai.expansion_locations_list
        print("Expansions: ", expansion_locations.__len__())

        for mf in self.ai.mineral_field:
            target: Point2 = mf.position
            center = target.closest(expansion_locations)
            target = target.towards(center, MINING_RADIUS)
            close = self.ai.mineral_field.closer_than(MINING_RADIUS, target)
            for mf2 in close:
                if mf2.tag != mf.tag:
                    points = get_intersections(mf.position, MINING_RADIUS, mf2.position, MINING_RADIUS)
                    if len(points) == 2:
                        target = center.closest(points)
            self.mineral_target_dict[mf.position] = target