from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Set

from bot.buildings.addon_swap.swap_plan import SwapPlan, SwapState
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

if TYPE_CHECKING:
    from bot.superbot import Superbot


_LIFT_ABILITY: dict[UnitTypeId, AbilityId] = {
    UnitTypeId.BARRACKS: AbilityId.LIFT_BARRACKS,
    UnitTypeId.FACTORY: AbilityId.LIFT_FACTORY,
    UnitTypeId.STARPORT: AbilityId.LIFT_STARPORT,
}


class AddonSwapManager:
    """
    Orchestrates an arbitrary number of concurrent addon swaps declared in the
    active build order.

    Each swap is represented by a SwapPlan and progresses through its own
    state machine independently. The manager only issues game commands;
    all unit lookups are delegated to SwapPlan properties.

    Integration points
    ------------------
    * Call register_swaps() when a build order is loaded.
    * Call on_step() every game step.
    * Call on_unit_destroyed() from the bot's on_unit_destroyed hook.
    * Query managed_tags to exclude managed buildings from reposition_buildings.
    """

    def __init__(self, bot: Superbot) -> None:
        self.bot: Superbot = bot
        self.swaps: List[SwapPlan] = []

    # Approximate game steps between repeated "waiting" prints (≈ 4 seconds).
    WAIT_PRINT_INTERVAL: int = 88

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_swaps(self, swaps: List[SwapPlan]) -> None:
        """Register the list of swaps for the current build order."""
        self.swaps = list(swaps)
        print(f"[AddonSwapManager] Registered {len(self.swaps)} swap(s).")
        for swap in self.swaps:
            print(f"[AddonSwapManager]   → {swap.donor_type.name} cedes {swap.desired_addon_type.name} to {swap.recipient_type.name}")

    def on_unit_destroyed(self, tag: int) -> None:
        """
        React to a unit being destroyed.

        - Addon destroyed mid-swap: always reset. The build order will detect the
          addon step is unsatisfied and rebuild it automatically.
        - Donor or recipient destroyed: reset if build order still running, abort otherwise.
        """
        for swap in self.swaps:
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

    @property
    def managed_tags(self) -> Set[int]:
        """Tags of all buildings currently mid-swap (donor, recipient, addon)."""
        tags: Set[int] = set()
        for swap in self.swaps:
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
        for swap in self.swaps:
            if (swap.state == SwapState.DONE or swap.state == SwapState.ABORTED):
                continue
            self.process(swap)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def process(self, swap: SwapPlan) -> None:
        match swap.state:
            case SwapState.PENDING:
                self.initiate(swap)
            case SwapState.DONOR_LIFTING:
                self.donor_lifting(swap)
            case SwapState.RECIPIENT_LIFTING_FIRST:
                self.recipient_lifting_first(swap)
            case SwapState.RECIPIENT_LIFTING:
                self.recipient_lifting(swap)
            case SwapState.RECIPIENT_LANDING:
                self.recipient_landing(swap)
            case SwapState.DONOR_LANDING:
                self.donor_landing(swap)

    # -- PENDING → DONOR_LIFTING or RECIPIENT_LIFTING_FIRST ----------------

    def initiate(self, swap: SwapPlan) -> None:
        """
        Initiate as soon as donor (with addon) and recipient both exist, and at
        least one of {addon, recipient} is ready.

        Path A — addon ready first (or both): lift donor → DONOR_LIFTING.
        Path B — recipient ready first: lift recipient → RECIPIENT_LIFTING_FIRST.
        """
        should_print: bool = (self.bot.state.game_loop % self.WAIT_PRINT_INTERVAL == 0)
        busy: Set[int] = self.managed_tags

        donor: Optional[Unit] = swap.find_donor(busy)
        if (donor is None):
            if (should_print):
                print(f"[AddonSwapManager] Waiting for donor: no {swap.donor_type.name} with/building {swap.desired_addon_type.name}.")
            return

        recipient: Optional[Unit] = swap.find_recipient(busy)
        if (recipient is None):
            if (should_print):
                print(f"[AddonSwapManager] Waiting for recipient: no {swap.recipient_type.name} found.")
            return

        addon_tag: Optional[int] = swap.detect_addon_tag(donor)
        addon: Optional[Unit] = self.bot.structures.find_by_tag(addon_tag) if (addon_tag is not None) else None

        addon_ready: bool = addon is not None and addon.is_ready
        recipient_ready: bool = recipient.is_ready

        if (should_print):
            print(
                f"[AddonSwapManager] donor={donor.tag} has_add_on={donor.has_add_on} "
                f"| addon_tag={addon_tag} addon_ready={addon_ready} "
                f"| recipient={recipient.tag} recipient_ready={recipient_ready}"
            )

        if (not addon_ready and not recipient_ready):
            if (should_print):
                print(f"[AddonSwapManager] Waiting: neither addon nor recipient ready yet.")
            return

        swap.commit(donor, recipient, addon_tag)

        if (addon_ready):
            print(f"[AddonSwapManager] Path A — lifting donor {swap.donor_type.name} (tag={donor.tag}) first.")
            donor(AbilityId.STOP)
            donor(_LIFT_ABILITY[swap.donor_type], queue=True)
            swap.state = SwapState.DONOR_LIFTING
        else:
            print(f"[AddonSwapManager] Path B — lifting recipient {swap.recipient_type.name} (tag={recipient.tag}) first.")
            recipient(AbilityId.STOP)
            recipient(_LIFT_ABILITY[swap.recipient_type], queue=True)
            swap.state = SwapState.RECIPIENT_LIFTING_FIRST

    # -- RECIPIENT_LIFTING_FIRST -------------------------------------------

    def recipient_lifting_first(self, swap: SwapPlan) -> None:
        """
        Path B: re-issue recipient lift until airborne, then wait for addon to
        complete before lifting the donor. While waiting, move the donor toward
        the recipient's original position so it's already in motion when we lift.
        """
        if (swap.recipient_flying is None):
            grounded: Optional[Unit] = swap.recipient
            if (grounded is not None):
                grounded(AbilityId.STOP)
                grounded(_LIFT_ABILITY[swap.recipient_type], queue=True)
            return

        # Recipient is airborne — nudge the donor toward recipient's original position.
        donor: Optional[Unit] = swap.donor
        if (donor is not None and not donor.is_moving):
            assert swap.recipient_original_position is not None
            donor.move(swap.recipient_original_position)

        if (swap.addon is None or not swap.addon.is_ready):
            return

        if (donor is None):
            return

        print(f"[AddonSwapManager] Addon ready (Path B) — lifting donor {swap.donor_type.name} (tag={donor.tag}).")
        donor(AbilityId.STOP)
        donor(_LIFT_ABILITY[swap.donor_type], queue=True)
        swap.state = SwapState.DONOR_LIFTING

    # -- DONOR_LIFTING → RECIPIENT_LIFTING or RECIPIENT_LANDING ------------

    def donor_lifting(self, swap: SwapPlan) -> None:
        """
        Re-issue donor lift until airborne.
        Path A: lift recipient → RECIPIENT_LIFTING.
        Path B: recipient already flying → RECIPIENT_LANDING.
        """
        if (swap.donor_flying is None):
            grounded: Optional[Unit] = swap.donor
            if (grounded is not None):
                grounded(AbilityId.STOP)
                grounded(_LIFT_ABILITY[swap.donor_type], queue=True)
            return

        # Donor is airborne — move toward recipient's original position.
        assert swap.recipient_original_position is not None
        if (not swap.donor_flying.is_moving):
            swap.donor_flying.move(swap.recipient_original_position)

        if (swap.recipient_flying is not None):
            print(f"[AddonSwapManager] Donor airborne (Path B) — recipient already flying, proceeding to RECIPIENT_LANDING.")
            swap.state = SwapState.RECIPIENT_LANDING
            return

        grounded_recipient: Optional[Unit] = swap.recipient
        if (grounded_recipient is None):
            return

        print(f"[AddonSwapManager] Donor airborne (Path A) — lifting recipient {swap.recipient_type.name} (tag={grounded_recipient.tag}).")
        grounded_recipient(_LIFT_ABILITY[swap.recipient_type])
        swap.state = SwapState.RECIPIENT_LIFTING

    # -- RECIPIENT_LIFTING → RECIPIENT_LANDING -----------------------------

    def recipient_lifting(self, swap: SwapPlan) -> None:
        """Re-issue recipient lift until airborne, then proceed to landing."""
        if (swap.recipient_flying is None):
            grounded: Optional[Unit] = swap.recipient
            if (grounded is not None):
                grounded(_LIFT_ABILITY[swap.recipient_type])
            return

        if (swap.addon is not None):
            swap.recipient_flying.move(swap.addon.add_on_land_position)

        print(f"[AddonSwapManager] Recipient airborne — proceeding to RECIPIENT_LANDING.")
        swap.state = SwapState.RECIPIENT_LANDING

    # -- RECIPIENT_LANDING -------------------------------------------------

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

        print(f"[AddonSwapManager] Landing recipient {swap.recipient_type.name} on addon (tag={swap.addon_tag}) at {land_position}.")
        swap.recipient_flying(AbilityId.LAND, land_position)
        swap.state = SwapState.DONOR_LANDING

    # -- DONOR_LANDING -----------------------------------------------------

    def donor_landing(self, swap: SwapPlan) -> None:
        """
        Land the donor at a new position, in parallel with the recipient landing.
        Searches from recipient_original_position. Marks DONE once grounded.
        """
        if (swap.donor_flying is None):
            print(f"[AddonSwapManager] Donor grounded — swap DONE.")
            swap.state = SwapState.DONE
            return

        if (swap.donor_flying.is_moving):
            return

        assert swap.recipient_original_position is not None
        land_position: Point2 = dfs_in_pathing(
            self.bot,
            swap.recipient_original_position,
            swap.donor_type,
            self.bot.game_info.map_center,
            1,
            swap.donor_needs_addon_after_swap,
        )

        print(f"[AddonSwapManager] Landing donor {swap.donor_type.name} at {land_position}.")
        swap.donor_flying(AbilityId.LAND, land_position)