from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, List, Optional
from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonDetachSwap, AddonSwap, SwapPlan, SwapState
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.strategy.build_order.build_order_step import BuildOrderStep
# from sc2.bot_ai import BotAI
from bot.strategy.strategy_types import Situation
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.units import Units
from ...utils.unit_tags import reactors, techlabs

if TYPE_CHECKING:
    from bot.superbot import Superbot

def addon_group(addon_type: UnitTypeId) -> list[UnitTypeId]:
    """Return all addon types functionally equivalent to the given one."""
    if (addon_type in reactors):
        return reactors
    if (addon_type in techlabs):
        return techlabs
    return [addon_type]

# Owning production building for each concrete (non-generic) addon type.
addon_owner: dict[UnitTypeId, UnitTypeId] = {
    UnitTypeId.BARRACKSTECHLAB: UnitTypeId.BARRACKS,
    UnitTypeId.BARRACKSREACTOR: UnitTypeId.BARRACKS,
    UnitTypeId.FACTORYTECHLAB: UnitTypeId.FACTORY,
    UnitTypeId.FACTORYREACTOR: UnitTypeId.FACTORY,
    UnitTypeId.STARPORTTECHLAB: UnitTypeId.STARPORT,
    UnitTypeId.STARPORTREACTOR: UnitTypeId.STARPORT,
}

class BuildOrder(CachedClass):
    steps: List[BuildOrderStep]
    name: BuildOrderName
    swap_plans: List[SwapPlan]
    equivalences: dict[UnitTypeId, List[UnitTypeId]] = {
        UnitTypeId.SUPPLYDEPOT: [UnitTypeId.SUPPLYDEPOTLOWERED],
        UnitTypeId.BARRACKS: [UnitTypeId.BARRACKSFLYING],
        UnitTypeId.FACTORY: [UnitTypeId.FACTORYFLYING],
        UnitTypeId.STARPORT: [UnitTypeId.STARPORTFLYING],
        UnitTypeId.COMMANDCENTER: [
            UnitTypeId.COMMANDCENTERFLYING,
            UnitTypeId.ORBITALCOMMAND,
            UnitTypeId.ORBITALCOMMANDFLYING,
            UnitTypeId.PLANETARYFORTRESS,
        ],
        UnitTypeId.TECHLAB:[UnitTypeId.BARRACKSTECHLAB, UnitTypeId.FACTORYTECHLAB, UnitTypeId.STARPORTTECHLAB],
        UnitTypeId.REACTOR: [UnitTypeId.BARRACKSREACTOR, UnitTypeId.FACTORYREACTOR, UnitTypeId.STARPORTREACTOR],
        UnitTypeId.BARRACKSTECHLAB: [UnitTypeId.FACTORYTECHLAB, UnitTypeId.STARPORTTECHLAB, UnitTypeId.TECHLAB],
        UnitTypeId.BARRACKSREACTOR: [UnitTypeId.FACTORYREACTOR, UnitTypeId.STARPORTREACTOR, UnitTypeId.REACTOR],
        UnitTypeId.FACTORYTECHLAB: [UnitTypeId.BARRACKSTECHLAB, UnitTypeId.STARPORTTECHLAB, UnitTypeId.TECHLAB],
        UnitTypeId.FACTORYREACTOR: [UnitTypeId.BARRACKSREACTOR, UnitTypeId.STARPORTREACTOR, UnitTypeId.REACTOR],
        UnitTypeId.STARPORTTECHLAB: [UnitTypeId.BARRACKSTECHLAB, UnitTypeId.FACTORYTECHLAB, UnitTypeId.TECHLAB],
        UnitTypeId.STARPORTREACTOR: [UnitTypeId.BARRACKSREACTOR, UnitTypeId.FACTORYREACTOR, UnitTypeId.REACTOR],
    }
    in_base_cc: bool = False
    is_defensive_response: bool = False
    default_defensive_response: Optional[BuildOrder] = None
    defensive_responses: dict[Situation, BuildOrder] = {}

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.swap_plans = []

    @property
    def addon_transfer_map(self) -> dict[int, UnitTypeId]:
        """
        Maps addon_tag → desired_addon_type for every swap that is past PENDING.
        During and after a transfer, the addon's real in-game type may differ
        (e.g. REACTOR instead of FACTORYREACTOR) — this map lets unit_amount
        count it under the type the build order originally requested.
        """
        return {
            plan.addon_tag: plan.desired_addon_type
            for plan in self.swap_plans
            if plan.addon_tag is not None and plan.state != SwapState.PENDING
        }

    def unit_amount(self, unit_id: UnitTypeId, include_pending: bool = True) -> int:
        unit_ids: list[UnitTypeId] = [unit_id]
        if (unit_id in self.equivalences):
            unit_ids.extend(self.equivalences[unit_id])

        count: int = (
            self.bot.structures(unit_ids).ready.amount
            + self.bot.units(unit_ids).ready.amount
        )

        # For each transferring addon, adjust the count:
        # - its real in-game type may already be counted under unit_ids → subtract 1
        # - if its desired_addon_type matches unit_id → add 1 back
        if (include_pending):
            count += int(max(self.bot.already_pending(unit_id), self.bot.structures(unit_ids).not_ready.amount))

        return count

    def reconcile(self, previous_swap_plans: Optional[list[SwapPlan]] = None) -> None:
        plans_to_prepend: list[SwapPlan] = []
        current_addons: list[UnitTypeId] = [addon.type_id for addon in self.bot.structures(reactors + techlabs)]
        print("[reconcile] current addons:", current_addons)
        print("[reconcile] target addons:", self.current_addons)

        # Multiset diff: only addons present in the target but missing from
        # the concrete state are blocking. Surplus addons are not an issue
        # on their own — they become donors for a matching shortage below.
        current_counts: Counter[UnitTypeId] = Counter(current_addons)
        target_counts: Counter[UnitTypeId] = Counter(self.current_addons)
        missing_addons: list[UnitTypeId] = list((target_counts - current_counts).elements())
        surplus_addons: list[UnitTypeId] = list((current_counts - target_counts).elements())
        print("[reconcile] missing addons:", missing_addons)
        print("[reconcile] surplus addons:", surplus_addons)

        # For each missing addon, look for a surplus addon of the same
        # functional family (reactor/techlab) to reroute via an AddonSwap.
        for missing_type in missing_addons:
            recipient_type: Optional[UnitTypeId] = addon_owner.get(missing_type)
            if (recipient_type is None):
                continue  # generic addon target — no specific building to route it to

            group: list[UnitTypeId] = addon_group(missing_type)
            surplus_type: Optional[UnitTypeId] = next(
                (addon for addon in surplus_addons if addon in group and addon in addon_owner),
                None,
            )
            if (surplus_type is None):
                continue  # no spare donor addon of this family

            donor_type: UnitTypeId = addon_owner[surplus_type]
            surplus_addons.remove(surplus_type)

            addon_family: UnitTypeId = UnitTypeId.REACTOR if (missing_type in reactors) else UnitTypeId.TECHLAB
            print(
                f"[reconcile] surplus {surplus_type.name} ({donor_type.name}) covers missing "
                f"{missing_type.name} ({recipient_type.name}) — injecting AddonSwap."
            )
            plans_to_prepend.append(AddonSwap(self.bot, donor_type, recipient_type, addon_family))

        # In-progress swaps carried over from a previous build order (BO switch):
        # abort the ones this build order no longer needs, but keep driving the
        # ones that still deliver something this build order's target requires —
        # otherwise the donor/recipient are left stranded mid-transfer.
        for plan in previous_swap_plans or []:
            if (plan.is_finished or plan.state == SwapState.PENDING):
                continue

            group: list[UnitTypeId] = addon_group(plan.desired_addon_type)
            still_needed: bool = any(
                addon_owner.get(addon) == plan.recipient_type
                for addon in self.current_addons
                if addon in group
            )
            if (still_needed):
                print(f"[reconcile] Carrying over in-progress swap {plan.name} — still required.")
                plans_to_prepend.append(plan)
            else:
                print(f"[reconcile] Aborting in-progress swap {plan.name} — no longer needed.")
                plan.state = SwapState.ABORTED

        for plan in self.swap_plans:
            if (plan.state != SwapState.PENDING):
                continue

            desired_group: list[UnitTypeId] = addon_group(plan.desired_addon_type)

            # Case 1: recipient already has a functionally equivalent addon → DONE
            recipient_with_equivalent_addon: bool = any(
                structure.has_add_on
                and self.bot.structures.find_by_tag(structure.add_on_tag) is not None
                and self.bot.structures.find_by_tag(structure.add_on_tag).type_id in desired_group
                for structure in self.bot.structures(plan.recipient_type)
            )
            if (recipient_with_equivalent_addon):
                print(f"[reconcile] {plan.name} already satisfied (equivalent addon) — DONE.")
                plan.state = SwapState.DONE
                continue

            # Case 2: donor exists with a non-equivalent addon → inject detach swap
            donor_with_wrong_addon: bool = any(
                structure.has_add_on
                and self.bot.structures.find_by_tag(structure.add_on_tag) is not None
                and self.bot.structures.find_by_tag(structure.add_on_tag).type_id not in desired_group
                for structure in self.bot.structures(plan.donor_type)
            )
            if (donor_with_wrong_addon):
                print(f"[reconcile] {plan.name} donor has wrong addon — injecting AddonDetachSwap.")
                plans_to_prepend.append(AddonDetachSwap(
                    self.bot,
                    donor_type=plan.donor_type,
                ))
                continue

            # Case 3: donor doesn't exist yet, or has no addon → stay PENDING
            # print(f"[reconcile] {plan.name} stays PENDING.")

        self.swap_plans = plans_to_prepend + self.swap_plans
    
    @custom_cache_once_per_frame
    def steps_completed(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if step.is_satisfied]

    @custom_cache_once_per_frame
    def steps_remaining(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if not step.is_satisfied]
    
    @custom_cache_once_per_frame
    def pending_steps(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if not step.is_satisfied and step.is_available]
    
    @custom_cache_once_per_frame
    def current_addons(self) -> List[UnitTypeId]:
        addons: List[UnitTypeId] = []
        for step in self.steps:
            if (step.is_satisfied and step.step_id in reactors + techlabs):
                addons.append(step.step_id)
        return addons

    @custom_cache_once_per_frame
    def next(self) -> BuildOrderStep | None:
        return next((step for step in self.steps if not step.is_satisfied), None)
    
    @custom_cache_once_per_frame
    def pending_ids(self) -> List[UnitTypeId | UpgradeId]:
        return [step.step_id for step in self.pending_steps]
    
    @custom_cache_once_per_frame
    def is_completed(self) -> bool:
        # Default that 4 bases = BO completed (to avoid weird bugs)
        return (
            self.bot.townhalls.amount >= 4
            or (
                all(step.is_satisfied for step in self.steps)
                and all(plan.is_finished for plan in self.swap_plans)
            )
        )
    
    @property
    def buildings_cut(self) -> List[UnitTypeId]:
        return []
    
    def modify_composition(self, composition: Composition) -> bool:
        if (self.is_completed):
            return False
        return self._modify_composition(composition)
    
    def _modify_composition(self, composition: Composition) -> bool:
        return False
    
    def get_defensive_response(self, situation: Situation) -> BuildOrder | None:
        specific_response: BuildOrder | None = self.defensive_responses.get(situation, None)
        if (specific_response is not None):
            return specific_response
        
        if (situation.is_cheese):
            return self.default_defensive_response
        
        return None