from __future__ import annotations

from typing import TYPE_CHECKING

from bot.strategy.build_order.addon_swap.state import SwapState
from bot.strategy.build_order.addon_swap.swap_plan import SwapPlan

if TYPE_CHECKING:
    from bot.strategy.build_order.addon_swap import AddonSwapManager


class AddonSwap(SwapPlan):
    """
    Standard addon swap: donor transfers its addon to a recipient building.

    State machine:
      Path A — PENDING → DONOR_LIFTING → RECIPIENT_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE
      Path B — PENDING → RECIPIENT_LIFTING_FIRST → DONOR_LIFTING → RECIPIENT_LANDING → DONOR_LANDING → DONE
    """

    def process(self, manager: AddonSwapManager) -> None:
        if (not self.condition()):
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