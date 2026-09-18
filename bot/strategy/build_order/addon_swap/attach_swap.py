from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Set

from bot.strategy.build_order.addon_swap.abilities import LIFT_ABILITY
from bot.strategy.build_order.addon_swap.state import SwapState
from bot.strategy.build_order.addon_swap.swap_plan import SwapPlan
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from bot.strategy.build_order.addon_swap.manager import AddonSwapManager


class AddonAttachSwap(SwapPlan):
    """
    Attach-only swap: a recipient building with no addon lifts off and lands
    on a free-standing (orphaned) addon. No donor building involved.

    State machine: PENDING → RECIPIENT_LIFTING → RECIPIENT_LANDING → DONE
    """

    def __init__(
        self,
        bot: BotAI,
        recipient_type: UnitTypeId,
        desired_addon_type: UnitTypeId,
        condition: Optional[callable[[], bool]] = None,
    ) -> None:
        # donor_type == recipient_type : hack délibéré pour que les propriétés
        # `donor`/`recipient` de SwapPlan (qui exigent toutes deux un tag non
        # None) se résolvent correctement une fois commit() appelé avec le
        # même Unit des deux côtés — sans ça get_addon_id() et LIFT_ABILITY
        # se basent sur le mauvais type de bâtiment (cf bug #2 ci-dessus).
        super().__init__(
            bot=bot,
            donor_type=recipient_type,
            recipient_type=recipient_type,
            desired_addon_type=desired_addon_type,
            condition=condition,
        )
        # L'addon qu'on cherche est libre au sol, donc son type_id en jeu est
        # le générique Reactor/Techlab — pas le type concrétisé par
        # get_addon_id() ci-dessus (ex: BARRACKSTECHLAB), qui ne correspond
        # qu'à un addon encore attaché.
        self.generic_addon_type: UnitTypeId = desired_addon_type

    @property
    def name(self) -> str:
        return f'AttachAddon ({self.recipient_type.name})'

    def __repr__(self) -> str:
        return f"AddonAttachSwap({self.recipient_type.name}, state={self.state.value})"

    def process(self, manager: AddonSwapManager) -> None:
        match self.state:
            case SwapState.PENDING:
                self._initiate(manager)
            case SwapState.RECIPIENT_LIFTING:
                manager.recipient_lifting(self)
            case SwapState.RECIPIENT_LANDING:
                self._recipient_landing()

    def _initiate(self, manager: AddonSwapManager) -> None:
        """Find a free-standing addon and a recipient without one."""
        busy: Set[int] = manager.managed_tags

        free_addons: Units = self.bot.structures(self.generic_addon_type).filter(
            lambda a: a.tag not in busy and a.is_ready
        )
        if (free_addons.amount == 0):
            return

        potential_recipients: Units = self.bot.structures(self.recipient_type).filter(
            lambda b: b.tag not in busy and not b.has_add_on and b.is_ready
        )
        if (potential_recipients.amount == 0):
            return

        addon: Unit = free_addons.first
        recipient: Unit = potential_recipients.closest_to(addon)

        # donor == recipient ici (cf commentaire dans __init__)
        self.commit(recipient, recipient, addon.tag)

        print(f"[AddonAttachSwap] Lifting {self.recipient_type.name} (tag={recipient.tag}) to attach free {addon.type_id.name}.")
        recipient(LIFT_ABILITY[self.recipient_type])
        self.state = SwapState.RECIPIENT_LIFTING

    def _recipient_landing(self) -> None:
        """Comme manager.recipient_landing(), mais finit à DONE au lieu de
        DONOR_LANDING (il n'y a pas de donor à faire atterrir ici)."""
        if (self.recipient_flying is None):
            return

        if (self.addon is None):
            print(f"[AddonAttachSwap] Target addon (tag={self.addon_tag}) lost — resetting swap.")
            self.reset()
            return

        land_position = self.addon.add_on_land_position

        if (not self.bot.in_placement_grid(land_position)):
            self.recipient_flying.move(land_position)
            return

        print(f"[AddonAttachSwap] Landing {self.recipient_type.name} on addon at {land_position}.")
        self.recipient_flying(AbilityId.LAND, land_position)
        self.state = SwapState.DONE