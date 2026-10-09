from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Callable, List, Optional
from bot.army_composition.composition import Composition
from sc2.ids.unit_typeid import UnitTypeId

if TYPE_CHECKING:
    from bot.superbot import Superbot

# Units each production building can train (morphed forms are covered by Superbot.equivalences)
production_units: dict[UnitTypeId, List[UnitTypeId]] = {
    UnitTypeId.BARRACKS: [UnitTypeId.MARINE, UnitTypeId.REAPER, UnitTypeId.MARAUDER, UnitTypeId.GHOST],
    UnitTypeId.FACTORY: [UnitTypeId.HELLION, UnitTypeId.WIDOWMINE, UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK, UnitTypeId.THOR],
    UnitTypeId.STARPORT: [UnitTypeId.VIKINGFIGHTER, UnitTypeId.MEDIVAC, UnitTypeId.LIBERATOR, UnitTypeId.BANSHEE, UnitTypeId.RAVEN, UnitTypeId.BATTLECRUISER],
}

class ProductionQueue:
    """
    Ordered list of units a production building type has to train before
    going back to the regular composition, e.g. [(REAPER, 4), (MARINE, 1)].
    Progress is measured on units *produced* this game (popped + in production),
    not on units alive: a unit dying is never replaced by the queue.
    While active, every other unit of that building is frozen at its current count.
    """
    bot: Superbot
    building_type: UnitTypeId
    units: List[tuple[UnitTypeId, int]]
    start_when: Optional[Callable[[], bool]]
    hold_until: Optional[Callable[[], bool]]
    hold_composition: dict[UnitTypeId, int]
    started: bool

    def __init__(
        self,
        bot: Superbot,
        building_type: UnitTypeId,
        units: List[tuple[UnitTypeId, int]],
        start_when: Optional[Callable[[], bool]] = None,
        hold_until: Optional[Callable[[], bool]] = None,
        hold_composition: Optional[dict[UnitTypeId, int]] = None,
    ) -> None:
        """
        start_when: keep the building idle until this returns True, then start the queue
        (e.g. waiting for a techlab so the first units don't delay the build order).
        Once it has returned True the queue stays started, even if the condition goes back to False.
        hold_until: once the queue is exhausted, keep the building idle until this returns True
        (e.g. waiting for an addon before switching to normal production).
        hold_composition: amounts to keep *alive* during the hold (replaced if they die),
        unlike the queue entries which are only produced once.
        """
        self.bot = bot
        self.building_type = building_type
        self.units = units
        self.start_when = start_when
        self.hold_until = hold_until
        self.hold_composition = hold_composition or {}
        self.started = start_when is None

    @property
    def has_started(self) -> bool:
        if (not self.started and self.start_when is not None and self.start_when()):
            self.started = True
        return self.started

    @property
    def current(self) -> Optional[tuple[UnitTypeId, int]]:
        """(unit type, amount left to start) of the current queue entry, None once every entry is produced."""
        consumed: Counter[tuple[UnitTypeId, ...]] = Counter()
        for unit_type, amount in self.units:
            key: tuple[UnitTypeId, ...] = tuple(self.bot.equivalences(unit_type))
            available: int = self.bot.units_produced(unit_type) - consumed[key]
            if (available < amount):
                return unit_type, amount - available
            consumed[key] += amount
        return None

    @property
    def is_active(self) -> bool:
        return (
            not self.has_started
            or self.current is not None
            or (self.hold_until is not None and not self.hold_until())
        )

    def apply(self, composition: Composition) -> bool:
        if (not self.is_active):
            return False

        for unit_type in production_units[self.building_type]:
            composition.set(unit_type, self.bot.total_unit_amount(unit_type))

        if (not self.has_started):
            return True

        current: Optional[tuple[UnitTypeId, int]] = self.current
        if (current is not None):
            unit_type, remaining = current
            composition.set(unit_type, self.bot.total_unit_amount(unit_type) + remaining)
        else:
            for unit_type, amount in self.hold_composition.items():
                composition.set(unit_type, amount)
        return True
