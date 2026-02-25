from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional, Set

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI


class SwapState(str, Enum):
    """
    Lifecycle of an addon swap between a donor and a recipient building.
    Two possible initiation paths depending on which building finishes first:

    Path A — donor (addon) ready first:
      PENDING → DONOR_LIFTING → RECIPIENT_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE

    Path B — recipient ready first:
      PENDING → RECIPIENT_LIFTING_FIRST → DONOR_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE
    """

    PENDING = "PENDING"
    DONOR_LIFTING = "DONOR_LIFTING"
    RECIPIENT_LIFTING_FIRST = "RECIPIENT_LIFTING_FIRST"
    RECIPIENT_LIFTING = "RECIPIENT_LIFTING"
    RECIPIENT_LANDING = "RECIPIENT_LANDING"
    DONOR_LANDING = "DONOR_LANDING"
    DONE = "DONE"
    ABORTED = "ABORTED"


class SwapPlan:
    """
    Declares the intent to swap an addon from a donor building to a recipient,
    and holds all runtime state for the swap.

    Static parameters (set at construction time)
    --------------------------------------------
    bot:
        Reference to the bot, used by all property lookups.
    donor_type:
        UnitTypeId of the grounded donor (e.g. FACTORY).
    donor_flying_type:
        UnitTypeId of the donor when airborne (e.g. FACTORYFLYING).
    recipient_type:
        UnitTypeId of the grounded recipient (e.g. STARPORT).
    recipient_flying_type:
        UnitTypeId of the recipient when airborne (e.g. STARPORTFLYING).
    desired_addon_type:
        The addon being transferred (e.g. FACTORYREACTOR).
    donor_needs_addon_after_swap:
        If True, the donor's new landing spot must have room for a future addon.
    """

    def __init__(
        self,
        bot: BotAI,
        donor_type: UnitTypeId,
        donor_flying_type: UnitTypeId,
        recipient_type: UnitTypeId,
        recipient_flying_type: UnitTypeId,
        desired_addon_type: UnitTypeId,
        donor_needs_addon_after_swap: bool = True,
    ) -> None:
        self.bot: BotAI = bot

        # Static parameters
        self.donor_type: UnitTypeId = donor_type
        self.donor_flying_type: UnitTypeId = donor_flying_type
        self.recipient_type: UnitTypeId = recipient_type
        self.recipient_flying_type: UnitTypeId = recipient_flying_type
        self.desired_addon_type: UnitTypeId = desired_addon_type
        self.donor_needs_addon_after_swap: bool = donor_needs_addon_after_swap

        # Runtime state — set via commit(), cleared via reset()
        self.donor_tag: Optional[int] = None
        self.recipient_tag: Optional[int] = None
        self.addon_tag: Optional[int] = None
        self.donor_original_position: Optional[Point2] = None
        self.recipient_original_position: Optional[Point2] = None
        self.state: SwapState = SwapState.PENDING

    def __repr__(self) -> str:
        return (
            f"SwapPlan({self.donor_type.name} → {self.recipient_type.name} "
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

    def commit(self, donor: Unit, recipient: Unit, addon_tag: Optional[int]) -> None:
        """
        Assign all runtime fields at the moment the swap is initiated.
        Called once by the manager when conditions are met.
        """
        self.donor_tag = donor.tag
        self.recipient_tag = recipient.tag
        self.addon_tag = addon_tag
        self.donor_original_position = donor.position
        self.recipient_original_position = recipient.position

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
    # Search properties (used while PENDING — no tags set yet)
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

        # Case 2: donor is currently building the addon (exists but build_progress < 1).
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