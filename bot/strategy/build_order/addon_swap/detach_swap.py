from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Set

from bot.strategy.build_order.addon_swap.abilities import LIFT_ABILITY
from bot.strategy.build_order.addon_swap.state import SwapState
from bot.strategy.build_order.addon_swap.swap_plan import SwapPlan
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from bot.strategy.build_order.addon_swap import AddonSwapManager


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
            desired_addon_type=UnitTypeId.TECHLAB,    # unused — any addon qualifies
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
            print(f"[AddonDetachSwap] No available donor of type {self.donor_type.name} — busy tags: {busy}")
            return

        # Reserve immediately so no other swap can steal this donor before commit.
        self.reserved_donor_tag = donor.tag
        self.commit(donor, None, donor.add_on_tag if donor.has_add_on else None)

        print(f"[AddonDetachSwap] Lifting {self.donor_type.name} (tag={donor.tag}) to detach addon.")
        donor(AbilityId.STOP)
        donor(LIFT_ABILITY[self.donor_type], queue=True)
        self.state = SwapState.DONOR_LIFTING