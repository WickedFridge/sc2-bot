from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class Bunker(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BUNKER
        self.name = "Bunker"
        self.ignore_build_order = True

    @property
    def _defense_structures(self) -> Units:
        return self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS])

    @property
    def _has_minimum_army(self) -> bool:
        reaper_amount = self.bot.units(UnitTypeId.REAPER).amount + self.bot.already_pending(UnitTypeId.REAPER)
        marine_amount = self.bot.units(UnitTypeId.MARINE).amount + self.bot.already_pending(UnitTypeId.MARINE)
        return reaper_amount >= 1 or marine_amount >= 2

    @property
    def _total_defense_count(self) -> float:
        return self._defense_structures.ready.amount + max(
            self.bot.already_pending(UnitTypeId.BUNKER),
            self.bot.structures(UnitTypeId.BUNKER).not_ready.amount
        )

    @property
    def _orphaned_bunker_count(self) -> int:
        if self.bot.expansions.amount_taken == 0:
            return 0
        return self.bot.structures(UnitTypeId.BUNKER).filter(
            lambda bunker: not self.bot.expansions.closest_to(bunker).is_taken
        ).amount

    @property
    def _active_defense_count(self) -> float:
        return self._total_defense_count - self._orphaned_bunker_count

    @property
    def _needs_main_bunker(self) -> bool:
        ramp_bunkers = self.bot.structures(UnitTypeId.BUNKER).filter(
            lambda b: b.distance_to(self.bot.main_base_ramp.top_center) < 8
        )
        if (ramp_bunkers.amount >= 1):
            return True
        if (not self.precarious):
            return False
        
        marine_amount = self.bot.units(UnitTypeId.MARINE).amount + self.bot.already_pending(UnitTypeId.MARINE)
        expansions_count = self.bot.expansions.amount_taken
        return (
            expansions_count == 1
            or (expansions_count == 2 and marine_amount >= 4)
        )

    @property
    def _bunker_target(self) -> int:
        target = self.bot.expansions.amount_taken - 1
        if self._needs_main_bunker:
            target += 1
        return target

    @property
    def _bunker_placement_pending(self) -> bool:
        return (
            self.bot.already_pending(UnitTypeId.BUNKER) - self.bot.structures(UnitTypeId.BUNKER).not_ready.amount
        ) > 0

    @property
    def expansions_without_defense(self) -> Expansions:
        expansions: Expansions = self.bot.expansions.taken.without_main

        # build a bunker in the main if we're getting proxy'd
        if (
            self.precarious
            and (
                self.bot.expansions.taken.amount == 1
                or (
                    self.bot.expansions.taken.amount == 2
                    and not self.bot.expansions.b2.is_defended
                )
            )
        ):
            expansions.add(self.bot.expansions.main)

        defense = self._defense_structures
        return expansions.filter(
            lambda expansion: (
                defense.amount == 0
                or defense.closest_distance_to(expansion.position) > 12
            )
        )

    @property
    @override
    def custom_conditions(self) -> bool:
        return (
            self._has_minimum_army
            and self.expansions_without_defense.amount >= 1
            and self._active_defense_count < self._bunker_target
            and not self._bunker_placement_pending
        )

    @property
    @override
    def position(self) -> Point2:
        # if there's already a bunker finished at the natural and we're on b2, additional bunkers should go on the natural
        if (
            self.bot.expansions.taken.amount == 2
            and self.bot.expansions.b2.is_defended
        ):
            return self.bot.expansions.b2.bunker_position
        expansion_not_defended: Expansion = self.expansions_without_defense.first
        return expansion_not_defended.bunker_position
