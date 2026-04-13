from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from bot.army_composition.composition import Composition
from bot.strategy.build_order.addon_swap import AddonDetachSwap, SwapPlan, SwapState
from bot.strategy.build_order.build_order_step import BuildOrderStep
# from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit
from ...utils.unit_tags import reactors, techlabs

if TYPE_CHECKING:
    from bot.superbot import Superbot

def _addon_group(addon_type: UnitTypeId) -> list[UnitTypeId]:
    """Return all addon types functionally equivalent to the given one."""
    if (addon_type in reactors):
        return reactors
    if (addon_type in techlabs):
        return techlabs
    return [addon_type]

class BuildOrder:
    bot: Superbot
    steps: List[BuildOrderStep]
    name: str
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

    def __init__(self, bot: Superbot):
        self.bot = bot
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
        # Net effect: +1 if desired matches and real doesn't, -1 if real matches and desired doesn't, 0 if both or neither match.
        # for tag, desired_type in self.addon_transfer_map.items():
        #     addon: Optional[Unit] = self.bot.structures.find_by_tag(tag)
        #     if (addon is None):
        #         continue
        #     if (addon.type_id in unit_ids):
        #         count -= 1
        #     if (desired_type == unit_id):
        #         count += 1

        if (include_pending):
            count += max(self.bot.already_pending(unit_id), self.bot.structures(unit_ids).not_ready.amount)

        return count

    def reconcile(self) -> None:
        plans_to_prepend: list[AddonDetachSwap] = []

        for plan in self.swap_plans:
            if (plan.state != SwapState.PENDING):
                continue

            desired_group: list[UnitTypeId] = _addon_group(plan.desired_addon_type)

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
                    donor_flying_type=plan.donor_flying_type,
                ))
                continue

            # Case 3: donor doesn't exist yet, or has no addon → stay PENDING
            # print(f"[reconcile] {plan.name} stays PENDING.")

        self.swap_plans = plans_to_prepend + self.swap_plans
    
    # steps not yet completed
    @property
    def steps_remaining(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if not step.is_satisfied]
    
    @property
    def pending_steps(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if not step.is_satisfied and step.is_available]
    
    # next step to execute
    @property
    def next(self) -> BuildOrderStep | None:
        return next((step for step in self.steps if not step.is_satisfied), None)
    
    @property
    def pending_ids(self) -> List[UnitTypeId | UpgradeId]:
        return [step.step_id for step in self.pending_steps]
    
    @property
    def is_completed(self) -> bool:
        # Default that 4 bases = BO completed (to avoid weird bugs)
        return (
            self.bot.townhalls.amount >= 4
            or all(step.is_satisfied for step in self.steps)
        )
    
    @property
    def buildings_cut(self) -> List[UnitTypeId]:
        return []
    
    def modify_composition(self, composition: Composition) -> None:
        pass