
from typing import List, Optional
from bot.army_composition.composition import Composition
from bot.buildings.addon_swap.swap_plan import SwapPlan, SwapState
from bot.strategy.build_order.build_order_step import BuildOrderStep
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit


class BuildOrder:
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
    }

    def __init__(self, bot: BotAI):
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
        for tag, desired_type in self.addon_transfer_map.items():
            addon: Optional[Unit] = self.bot.structures.find_by_tag(tag)
            if (addon is None):
                continue
            if (addon.type_id in unit_ids):
                count -= 1
            if (desired_type == unit_id):
                count += 1

        if (include_pending):
            count += self.bot.already_pending(unit_id)

        return count

    # steps not yet completed
    @property
    def steps_remaining(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if not step.is_satisfied]
    
    # next step to execute
    @property
    def next(self) -> BuildOrderStep | None:
        return next((step for step in self.steps if not step.is_satisfied), None)
    
    @property
    def pending_ids(self) -> List[UnitTypeId | UpgradeId]:
        return [step.step_id for step in self.steps if not step.is_satisfied and step.is_available]
    
    @property
    def is_completed(self) -> bool:
        return all(step.is_satisfied for step in self.steps)
    
    def modify_composition(self, composition: Composition) -> None:
        pass