from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Optional, Set

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from bot.strategy.build_order.addon_swap.manager import AddonSwapManager


class SwapState(str, Enum):
    """
    Lifecycle of an addon swap between a donor and a recipient building.
    Two possible initiation paths depending on which building finishes first:

    Path A — donor (addon) ready first:
      PENDING → DONOR_LIFTING → RECIPIENT_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE

    Path B — recipient ready first:
      PENDING → RECIPIENT_LIFTING_FIRST → DONOR_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE

    Detach-only path (AddonDetachSwap):
      PENDING → DONOR_LIFTING → DONOR_LANDING → DONE
    """

    PENDING = "PENDING"
    DONOR_LIFTING = "DONOR_LIFTING"
    RECIPIENT_LIFTING_FIRST = "RECIPIENT_LIFTING_FIRST"
    RECIPIENT_LIFTING = "RECIPIENT_LIFTING"
    RECIPIENT_LANDING = "RECIPIENT_LANDING"
    DONOR_LANDING = "DONOR_LANDING"
    DONE = "DONE"
    ABORTED = "ABORTED"


_LIFT_ABILITY: dict[UnitTypeId, AbilityId] = {
    UnitTypeId.BARRACKS: AbilityId.LIFT_BARRACKS,
    UnitTypeId.FACTORY: AbilityId.LIFT_FACTORY,
    UnitTypeId.STARPORT: AbilityId.LIFT_STARPORT,
}


class SwapPlan(ABC):
    """
    Abstract base for all addon swap plans.

    Subclasses implement process() to drive their own state machine,
    and may delegate individual states back to AddonSwapManager methods.
    """
    condition: callable[[], bool]  # Optional additional condition that must be true to initiate the swap

    def __init__(
        self,
        bot: BotAI,
        donor_type: UnitTypeId,
        donor_flying_type: UnitTypeId,
        recipient_type: UnitTypeId,
        recipient_flying_type: UnitTypeId,
        desired_addon_type: UnitTypeId,
        condition: Optional[callable[[], bool]] = None,
    ) -> None:
        self.bot: BotAI = bot

        # Static parameters
        self.donor_type: UnitTypeId = donor_type
        self.donor_flying_type: UnitTypeId = donor_flying_type
        self.recipient_type: UnitTypeId = recipient_type
        self.recipient_flying_type: UnitTypeId = recipient_flying_type
        self.desired_addon_type: UnitTypeId = desired_addon_type

        # Runtime state — set via commit(), cleared via reset()
        self.donor_tag: Optional[int] = None
        self.recipient_tag: Optional[int] = None
        self.addon_tag: Optional[int] = None
        self.donor_original_position: Optional[Point2] = None
        self.recipient_original_position: Optional[Point2] = None
        self.state: SwapState = SwapState.PENDING
        if (condition is not None):
            self.condition: callable[[], bool] = condition
        else:
            self.condition: callable[[], bool] = lambda: True
    @property
    def name(self) -> str:
        return f'{self.desired_addon_type.name} ({self.donor_type.name} -> {self.recipient_type.name})'

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.donor_type.name} → {self.recipient_type.name} "
            f"via {self.desired_addon_type.name}, state={self.state.value})"
        )

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """True while the swap is in progress (at least one building is flying)."""
        return self.state not in (SwapState.PENDING, SwapState.DONE, SwapState.ABORTED)

    @property
    def is_finished(self) -> bool:
        return self.state in (SwapState.DONE, SwapState.ABORTED)

    def commit(self, donor: Unit, recipient: Optional[Unit], addon_tag: Optional[int]) -> None:
        """
        Assign all runtime fields at the moment the swap is initiated.
        recipient may be None for detach-only swaps.
        """
        self.donor_tag = donor.tag
        self.recipient_tag = recipient.tag if recipient is not None else None
        self.addon_tag = addon_tag
        self.donor_original_position = donor.position
        self.recipient_original_position = recipient.position if recipient is not None else donor.position

    def reset(self) -> None:
        """Clear all runtime state so the swap can be retried from PENDING."""
        self.donor_tag = None
        self.recipient_tag = None
        self.addon_tag = None
        self.donor_original_position = None
        self.recipient_original_position = None
        self.state = SwapState.PENDING

    # ------------------------------------------------------------------
    # Unit properties (require commit() to have been called)
    # ------------------------------------------------------------------

    @property
    def donor(self) -> Optional[Unit]:
        """The grounded donor unit, or None if not currently on the ground."""
        assert self.donor_tag is not None, "donor_tag must be set before resolving"
        return self.bot.structures(self.donor_type).find_by_tag(self.donor_tag)

    @property
    def donor_flying(self) -> Optional[Unit]:
        """The airborne donor unit, or None if not currently flying."""
        assert self.donor_tag is not None, "donor_tag must be set before resolving"
        return self.bot.structures(self.donor_flying_type).find_by_tag(self.donor_tag)

    @property
    def recipient(self) -> Optional[Unit]:
        """The grounded recipient unit, or None if not currently on the ground."""
        assert self.recipient_tag is not None, "recipient_tag must be set before resolving"
        return self.bot.structures(self.recipient_type).find_by_tag(self.recipient_tag)

    @property
    def recipient_flying(self) -> Optional[Unit]:
        """The airborne recipient unit, or None if not currently flying."""
        assert self.recipient_tag is not None, "recipient_tag must be set before resolving"
        return self.bot.structures(self.recipient_flying_type).find_by_tag(self.recipient_tag)

    @property
    def addon(self) -> Optional[Unit]:
        """The tracked addon unit (any build state), or None if destroyed."""
        assert self.addon_tag is not None, "addon_tag must be set before resolving"
        return self.bot.structures.find_by_tag(self.addon_tag)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def process(self, manager: AddonSwapManager) -> None:
        """Advance the swap by one step. Called every game frame by the manager."""
        ...

    # ------------------------------------------------------------------
    # Search methods (used while PENDING — no tags set yet)
    # ------------------------------------------------------------------

    def find_donor(self, busy_tags: Set[int]) -> Optional[Unit]:
        """
        Search for an eligible donor: a grounded donor_type building that either
        has the desired addon attached or is currently building it.
        """
        # Case 1: donor has the completed addon attached.
        candidates: Units = self.bot.structures(self.donor_type).filter(
            lambda b: (
                b.tag not in busy_tags
                and self._addon_attached_matches(b)
            )
        )
        if (candidates):
            return candidates.first

        # Case 2: donor is currently building the addon (build_progress < 1).
        pending_addons: Units = self.bot.structures(self.desired_addon_type).filter(
            lambda a: a.build_progress < 1
        )
        for pending_addon in pending_addons:
            owner_candidates: Units = self.bot.structures(self.donor_type).filter(
                lambda b: (
                    b.tag not in busy_tags
                    and b.position.distance_to(pending_addon.add_on_land_position) < 1
                )
            )
            if (owner_candidates):
                return owner_candidates.first

        return None

    def find_recipient(self, busy_tags: Set[int]) -> Optional[Unit]:
        """
        Search for an eligible recipient: a grounded recipient_type building
        with no addon, not already managed by another swap.
        """
        candidates: Units = self.bot.structures(self.recipient_type).filter(
            lambda b: (
                b.tag not in busy_tags
                and not b.has_add_on
                and not b.is_flying
            )
        )
        return candidates.first if candidates else None

    def detect_addon_tag(self, donor: Unit) -> Optional[int]:
        """
        Find the tag of the addon (complete or in-progress) associated with
        the given donor unit. Returns None if no addon is found.
        """
        # Case 1: addon is complete and attached.
        if (donor.has_add_on):
            attached: Optional[Unit] = self.bot.structures.find_by_tag(donor.add_on_tag)
            if (attached is not None and attached.type_id == self.desired_addon_type):
                return attached.tag

        # Case 2: addon is under construction — find by expected position.
        nearby: Units = self.bot.structures(self.desired_addon_type).filter(
            lambda a: a.position.distance_to(donor.add_on_position) < 1
        )
        return nearby.first.tag if nearby else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _addon_attached_matches(self, building: Unit) -> bool:
        """True if the building has a completed attached addon of desired_addon_type."""
        if (not building.has_add_on):
            return False
        attached: Optional[Unit] = self.bot.structures.find_by_tag(building.add_on_tag)
        if (attached is None):
            return False
        return attached.type_id == self.desired_addon_type


class AddonSwap(SwapPlan):
    """
    Standard addon swap: donor transfers its addon to a recipient building.

    State machine:
      Path A — PENDING → DONOR_LIFTING → RECIPIENT_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE
      Path B — PENDING → RECIPIENT_LIFTING_FIRST → DONOR_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE
    """

    def process(self, manager: AddonSwapManager) -> None:
        print(f'condition: {self.condition()}, state: {self.state}')
        if (self.condition is not None and not self.condition()):
            return
        match self.state:
            case SwapState.PENDING:
                manager.initiate(self)
            case SwapState.DONOR_LIFTING:
                manager.donor_lifting(self)
            case SwapState.RECIPIENT_LIFTING_FIRST:
                manager.recipient_lifting_first(self)
            case SwapState.RECIPIENT_LIFTING:
                manager.recipient_lifting(self)
            case SwapState.RECIPIENT_LANDING:
                manager.recipient_landing(self)
            case SwapState.DONOR_LANDING:
                manager.donor_landing(self)


class AddonDetachSwap(SwapPlan):
    """
    Detach-only swap: donor lifts off to drop its current addon, then lands
    elsewhere. No recipient involved.

    Used during build order transitions when a donor has the wrong addon type
    and needs to free itself before the correct addon can be built or swapped.

    State machine: PENDING → DONOR_LIFTING → DONOR_LANDING → DONE
    """

    def __init__(
        self,
        bot: BotAI,
        donor_type: UnitTypeId,
        donor_flying_type: UnitTypeId,
    ) -> None:
        super().__init__(
            bot=bot,
            donor_type=donor_type,
            donor_flying_type=donor_flying_type,
            recipient_type=donor_type,               # unused — no recipient
            recipient_flying_type=donor_flying_type,  # unused — no recipient
            desired_addon_type=UnitTypeId.INVALID,    # unused — any addon qualifies
        )

    @property
    def name(self) -> str:
        return f'DetachAddon ({self.donor_type.name})'

    def __repr__(self) -> str:
        return f"AddonDetachSwap({self.donor_type.name}, state={self.state.value})"

    def process(self, manager: AddonSwapManager) -> None:
        match self.state:
            case SwapState.PENDING:
                self._initiate(manager)
            case SwapState.DONOR_LIFTING:
                manager.donor_lifting(self)
            case SwapState.DONOR_LANDING:
                manager.donor_landing(self)

    def _initiate(self, manager: AddonSwapManager) -> None:
        """Find a donor with any addon and lift it."""
        busy: Set[int] = manager.managed_tags
        donor: Optional[Unit] = self.bot.structures(self.donor_type).filter(
            lambda b: b.tag not in busy and b.has_add_on and b.is_ready
        ).first
        if (donor is None):
            return

        # Commit with no recipient — recipient_original_position falls back to donor position.
        self.commit(donor, None, donor.add_on_tag if donor.has_add_on else None)

        print(f"[AddonDetachSwap] Lifting {self.donor_type.name} (tag={donor.tag}) to detach addon.")
        donor(AbilityId.STOP)
        donor(_LIFT_ABILITY[self.donor_type], queue=True)
        self.state = SwapState.DONOR_LIFTING