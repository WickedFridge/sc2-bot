from __future__ import annotations
from typing import List, TYPE_CHECKING

from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

if TYPE_CHECKING:
    from bot.strategy.build_order.build_order import BuildOrder

class BuildOrderStep:
    bot: BotAI
    build_order: BuildOrder
    name: str
    step_id: UnitTypeId | UpgradeId
    target_count: int
    workers: int
    supply: int
    army_supply: int
    townhalls: int
    requirements: tuple[UnitTypeId, int, bool]
    upgrades_required: List[UpgradeId]
    
    def __init__(
        self,
        bot: BotAI,
        build_order: BuildOrder,
        name: str,
        step_id: UnitTypeId | UpgradeId,
        target_count: int = 1,
        workers: int = 0,
        supply: int = 0,
        army_supply: int = 0,
        townhalls: int = 1,
        requirements: List[tuple[UnitTypeId, int, bool]] = None,
        upgrades_required: List[UpgradeId] = None,
    ) -> None:
        self.bot = bot
        self.build_order = build_order
        self.name = name
        self.step_id = step_id
        self.target_count = target_count
        self.workers = workers
        self.supply = supply
        self.army_supply = army_supply
        self.townhalls = townhalls
        self.requirements = requirements or []
        self.upgrades_required = upgrades_required or []
    
    @property
    def current_amount(self) -> int:
        if (isinstance(self.step_id, UpgradeId)):
            return self.bot.already_pending_upgrade(self.step_id) > 0
        return self.build_order.unit_amount(self.step_id)

    # def unit_amount(self, unit_id: UnitTypeId, include_pending: bool = True) -> int:
    #     unit_ids: list[UnitTypeId] = [unit_id]
    #     if (unit_id in self.equivalences.keys()):
    #         unit_ids.extend(self.equivalences[unit_id])

    #     count: int = (
    #         self.bot.structures(unit_ids).ready.amount
    #         + self.bot.units(unit_ids).ready.amount
    #     )

    #     # An addon mid-swap or post-swap may have a different in-game type_id
    #     # (e.g. REACTOR instead of FACTORYREACTOR). Count it under desired_addon_type.
    #     committed: dict[int, UnitTypeId] = self.build_order.addon_transfer_map
    #     for tag, desired_type in committed.items():
    #         if (desired_type == unit_id):
    #             count += 1

    #     if (include_pending):
    #         count += self.bot.already_pending(unit_id)

    #     return count
    
    @property
    def is_satisfied(self) -> bool:
        return self.current_amount >= self.target_count
    
    def is_available_debug(self) -> tuple[bool, str]:
        # if (self.is_satisfied):
        #     return True, ''
        if (self.bot.tech_requirement_progress(self.step_id) < 1.0):
            return False, f'(tech requirement not ready)'
        if (self.bot.townhalls.amount < self.townhalls):
            return False, f'(not enough townhalls)'
        if (self.bot.supply_used < self.supply):
            return False, f'(not enough supply)'
        if (self.bot.supply_army < self.army_supply):
            return False, f'(not enough army)'
        if (self.bot.supply_workers < self.workers):
            return False, f'(not enough workers)'
        for unit_type, amount_required, completed in self.requirements:
            unit_count: int = self.build_order.unit_amount(unit_type, include_pending=not completed)
            if (unit_count < amount_required):
                return False, f'(not enough {unit_type} ({unit_count}/{amount_required}))'
        for upgrade in self.upgrades_required:
            if (self.bot.already_pending_upgrade(upgrade) < 1):
                return False, f'(upgrade {upgrade} not ready)'
        return True, ''
    
    @property
    def is_available(self) -> bool:
        if (self.bot.tech_requirement_progress(self.step_id) < 1.0):
            return False
        if (self.bot.townhalls.amount < self.townhalls):
            return False
        if (self.bot.supply_used < self.supply):
            return False
        if (self.bot.supply_workers < self.workers):
            return False
        for unit_type, amount_required, completed in self.requirements:
            unit_count: int = self.build_order.unit_amount(unit_type, include_pending=not completed)
            if (unit_count < amount_required):
                return False
        for upgrade in self.upgrades_required:
            if (self.bot.already_pending_upgrade(upgrade) < 1):
                return False
        return True
    
    # def print_check(self) -> None:
    #     checked_character: str = 'X' if self.checked else ' '
    #     print(f'[{checked_character}] BO -- {self.name}')
