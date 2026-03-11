from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Set

from bot.strategy.build_order.addon_swap.abilities import LIFT_ABILITY
from bot.strategy.build_order.addon_swap.state import SwapState
from bot.strategy.build_order.addon_swap.swap_plan import SwapPlan
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

if TYPE_CHECKING:
    from bot.superbot import Superbot


class AddonSwapManager:
    """
    Orchestrates an arbitrary number of concurrent addon swaps declared in the
    active build order.

    Each swap is represented by a SwapPlan subclass and drives its own state
    machine via swap.process(self). The manager exposes individual state
    handler methods that SwapPlan subclasses delegate to.

    Integration points
    ------------------
    * Call on_step() every game step.
    * Call on_unit_destroyed() from the bot's on_unit_destroyed hook.
    * Query managed_tags to exclude managed buildings from reposition_buildings.
    """

    def __init__(self, bot: Superbot) -> None:
        self.bot: Superbot = bot

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def swap_plans(self) -> List[SwapPlan]:
        """Live reference to the active build order's swap plans."""
        return self.bot.build_order.build.swap_plans

    @property
    def managed_tags(self) -> Set[int]:
        """
        Tags of all buildings currently reserved or mid-swap.
        Includes reserved_donor_tag to protect PENDING detach swaps
        from being stolen by concurrent swaps.
        """
        tags: Set[int] = set()
        for swap in self.swap_plans:
            if (swap.is_finished):
                continue
            if (swap.reserved_donor_tag is not None):
                tags.add(swap.reserved_donor_tag)
            if (not swap.is_active):
                continue
            if (swap.donor_tag is not None):
                tags.add(swap.donor_tag)
            if (swap.recipient_tag is not None):
                tags.add(swap.recipient_tag)
            if (swap.addon_tag is not None):
                tags.add(swap.addon_tag)
        return tags

    def on_step(self) -> None:
        """Advance all registered swaps by one step."""
        for swap in self.swap_plans:
            if (swap.is_finished):
                continue
            if (swap.state == SwapState.CONDITION_NOT_MET):
                if (swap.condition()):
                    swap.state = SwapState.PENDING
                continue
            if (not swap.condition() and swap.state == SwapState.PENDING):
                swap.state = SwapState.CONDITION_NOT_MET
                continue
            swap.process(self)

    def on_unit_destroyed(self, tag: int) -> None:
        """
        React to a unit being destroyed.

        - Addon destroyed mid-swap: always reset.
        - Donor or recipient destroyed: reset if build order still running, abort otherwise.
        """
        for swap in self.swap_plans:
            if (swap.is_finished):
                continue

            if (tag == swap.addon_tag):
                print(f"[AddonSwapManager] Addon (tag={tag}) destroyed — resetting to PENDING.")
                swap.reset()
                continue

            if (tag not in (swap.donor_tag, swap.recipient_tag)):
                continue

            if (self.bot.build_order.build.is_completed):
                print(f"[AddonSwapManager] Building (tag={tag}) destroyed after build order — aborting swap.")
                swap.state = SwapState.ABORTED
            else:
                print(f"[AddonSwapManager] Building (tag={tag}) destroyed during build order — resetting swap.")
                swap.reset()

    # ------------------------------------------------------------------
    # State handlers — called by SwapPlan subclasses via process()
    # ------------------------------------------------------------------

    def recipient_lifting_first(self, swap: SwapPlan) -> None:
        """
        Path B: re-issue recipient lift until airborne, then wait for addon to
        complete before lifting the donor.
        """
        if (swap.recipient_flying is None):
            grounded: Optional[Unit] = swap.recipient
            if (grounded is not None):
                grounded(LIFT_ABILITY[swap.recipient_type])
            return

        # Recipient is airborne — position it above its future landing spot.
        donor: Optional[Unit] = swap.donor
        if (donor is None):
            return

        recipient_flying: Optional[Unit] = swap.recipient_flying
        if (recipient_flying is not None and not recipient_flying.is_moving):
            assert swap.donor_original_position is not None
            if (recipient_flying.distance_to(swap.donor_original_position) > 1):
                recipient_flying.move(swap.donor_original_position)

        if (swap.addon is None or not swap.addon.is_ready):
            return

        print(f"[AddonSwapManager] Addon ready (Path B) — lifting donor {swap.donor_type.name} (tag={donor.tag}).")
        donor(LIFT_ABILITY[swap.donor_type])
        swap.state = SwapState.DONOR_LIFTING

    def donor_lifting(self, swap: SwapPlan) -> None:
        """
        Re-issue donor lift until airborne, then issue a land order.
        - AddonDetachSwap (no recipient): go straight to DONOR_LANDING.
        - Path A: lift recipient → RECIPIENT_LIFTING.
        - Path B: recipient already flying → RECIPIENT_LANDING.
        """
        if (swap.donor_flying is None):
            grounded: Optional[Unit] = swap.donor
            if (grounded is not None):
                grounded(LIFT_ABILITY[swap.donor_type])
            return

        if (not swap.donor_flying.is_moving):
            top_position: Point2 = swap.donor_original_position + Point2((0, 2.5))
            land_position: Point2 = dfs_in_pathing(
                self.bot,
                top_position,
                swap.donor_type,
                self.bot.game_info.map_center,
                1.5,
                True,
            )
            swap.donor_flying(AbilityId.LAND, land_position)

        # AddonDetachSwap has no recipient — go straight to DONOR_LANDING.
        if (swap.recipient_tag is None):
            swap.state = SwapState.DONOR_LANDING
            return

        if (swap.recipient_flying is not None):
            print(f"[AddonSwapManager] Donor airborne (Path B) — recipient already flying.")
            swap.state = SwapState.RECIPIENT_LANDING
            return

        grounded_recipient: Optional[Unit] = swap.recipient
        if (grounded_recipient is None):
            return

        print(f"[AddonSwapManager] Donor airborne (Path A) — lifting recipient {swap.recipient_type.name} (tag={grounded_recipient.tag}).")
        grounded_recipient(LIFT_ABILITY[swap.recipient_type])
        swap.state = SwapState.RECIPIENT_LIFTING

    def recipient_lifting(self, swap: SwapPlan) -> None:
        """Re-issue recipient lift until airborne, then proceed to landing."""
        if (swap.recipient_flying is None):
            grounded: Optional[Unit] = swap.recipient
            if (grounded is not None):
                grounded(LIFT_ABILITY[swap.recipient_type])
            return

        swap.recipient_flying.move(swap.addon.add_on_land_position)

        print(f"[AddonSwapManager] Recipient airborne — proceeding to RECIPIENT_LANDING.")
        swap.state = SwapState.RECIPIENT_LANDING

    def recipient_landing(self, swap: SwapPlan) -> None:
        """
        Land the recipient on the tracked addon.
        Hover at the landing position while the donor's footprint is still occupied.
        """
        if (swap.recipient_flying is None):
            return

        if (swap.addon is None):
            print(f"[AddonSwapManager] Target addon (tag={swap.addon_tag}) lost — resetting swap.")
            swap.reset()
            return

        land_position: Point2 = swap.addon.add_on_land_position

        if (not self.bot.in_placement_grid(land_position)):
            swap.recipient_flying.move(land_position)
            return

        print(f"[AddonSwapManager] Landing recipient {swap.recipient_type.name} on addon at {land_position}.")
        swap.recipient_flying(AbilityId.LAND, land_position)
        swap.state = SwapState.DONOR_LANDING

    def donor_landing(self, swap: SwapPlan) -> None:
        """
        Land the donor at a free position near its original location.
        Marks DONE once grounded. Shared by AddonSwap and AddonDetachSwap.
        """
        if (swap.donor_flying is None):
            print(f"[AddonSwapManager] Donor grounded — swap DONE.")
            swap.state = SwapState.DONE
            return

        if (swap.donor_flying.is_moving):
            return

        top_position: Point2 = swap.donor_original_position + Point2((0, -2.5))
        bottom_position: Point2 = swap.donor_original_position + Point2((0, 2.5))

        free_position: Point2 = (
            top_position
            if self.bot.map.influence_maps.buildings.can_build(top_position, swap.donor_type)
            else bottom_position if self.bot.map.influence_maps.buildings.can_build(bottom_position, swap.donor_type)
            else swap.donor_original_position
        )

        land_position: Point2 = dfs_in_pathing(
            self.bot,
            free_position,
            swap.donor_type,
            self.bot.game_info.map_center,
            1.5,
            True,
        )

        print(f"[AddonSwapManager] Landing donor {swap.donor_type.name} at {land_position}.")
        swap.donor_flying(AbilityId.LAND, land_position)