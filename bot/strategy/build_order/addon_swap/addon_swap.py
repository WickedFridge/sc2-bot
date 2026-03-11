from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Set

from bot.strategy.build_order.addon_swap.abilities import LIFT_ABILITY
from bot.strategy.build_order.addon_swap.state import SwapState
from bot.strategy.build_order.addon_swap.swap_plan import SwapPlan
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit

if TYPE_CHECKING:
    from bot.strategy.build_order.addon_swap.manager import AddonSwapManager


class AddonSwap(SwapPlan):
    """
    Standard addon swap: donor transfers its addon to a recipient building.

    State machine:
      Path A — PENDING → DONOR_LIFTING → RECIPIENT_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE
      Path B — PENDING → RECIPIENT_LIFTING_FIRST → DONOR_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE
    """

    def process(self, manager: AddonSwapManager) -> None:
        match self.state:
            case SwapState.PENDING:
                self._initiate(manager)
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

    def _initiate(self, manager: AddonSwapManager) -> None:
        """
        Initiate as soon as donor (with addon) and recipient both exist, and at
        least one of {addon, recipient} is ready.

        Path A — addon ready first (or both): lift donor → DONOR_LIFTING.
        Path B — recipient ready first: lift recipient → RECIPIENT_LIFTING_FIRST.
        """
        busy: Set[int] = manager.managed_tags

        donor: Optional[Unit] = self.find_donor(busy)
        if (donor is None):
            return

        recipient: Optional[Unit] = self.find_recipient(busy)
        if (recipient is None):
            return

        addon_tag: Optional[int] = self.detect_addon_tag(donor)
        addon: Optional[Unit] = self.bot.structures.find_by_tag(addon_tag) if (addon_tag is not None) else None

        addon_ready: bool = addon is not None and addon.is_ready
        recipient_ready: bool = recipient.is_ready

        if (not addon_ready and not recipient_ready):
            return

        self.commit(donor, recipient, addon_tag)

        if (addon_ready):
            print(f"[AddonSwap] Path A — lifting donor {self.donor_type.name} (tag={donor.tag}) first.")
            donor(LIFT_ABILITY[self.donor_type])
            self.state = SwapState.DONOR_LIFTING
        else:
            print(f"[AddonSwap] Path B — lifting recipient {self.recipient_type.name} (tag={recipient.tag}) first.")
            recipient(LIFT_ABILITY[self.recipient_type])
            self.state = SwapState.RECIPIENT_LIFTING_FIRST