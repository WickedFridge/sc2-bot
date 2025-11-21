
from typing import List
from bot.army_composition.composition import Composition
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from bot.utils.unit_tags import build_order_structures

class BuildOrderStep:
    bot: BotAI
    step_id: UnitTypeId | UpgradeId
    workers: int
    supply: int
    townhalls: int
    requirements: tuple[UnitTypeId, int, bool]
    upgrades_required: List[UpgradeId]
    checked: bool = False
    
    def __init__(
        self,
        bot: BotAI,
        name: str,
        step_id: UnitTypeId | UpgradeId,
        workers: int = 0,
        supply: int = 0,
        townhalls: int = 1,
        requirements: List[tuple[UnitTypeId, int, bool]] = None,
        upgrades_required: List[UpgradeId] = None,
    ) -> None:
        self.bot = bot
        self.name = name
        self.step_id = step_id
        self.workers = workers
        self.supply = supply
        self.townhalls = townhalls
        self.requirements = requirements or []
        self.upgrades_required = upgrades_required or []

    def can_check_debug(self) -> tuple[bool, str]:
        if (self.bot.tech_requirement_progress(self.step_id) < 1.0):
            return False, f'(tech requirement not ready)'
        if (self.bot.townhalls.amount < self.townhalls):
            return False, f'(not enough townhalls)'
        if (self.bot.supply_used < self.supply):
            return False, f'(not enough supply)'
        if (self.bot.supply_workers < self.workers):
            return False, f'(not enough workers)'
        for unit_type, amount_required, completed in self.requirements:
            unit_count: int = (
                self.bot.structures(unit_type).ready.amount
                + self.bot.units(unit_type).ready.amount
            )
            if (not completed):
                unit_count += self.bot.already_pending(unit_type)
            if (unit_count < amount_required):
                return False, f'(not enough {unit_type} ({unit_count}/{amount_required}))'
        for upgrade in self.upgrades_required:
            if (self.bot.already_pending_upgrade(upgrade) < 1):
                return False, f'(upgrade {upgrade} not ready)'
        return True, ''
    
    @property
    def can_check(self) -> bool:
        if (self.bot.tech_requirement_progress(self.step_id) < 1.0):
            return False
        if (self.bot.townhalls.amount < self.townhalls):
            return False
        if (self.bot.supply_used < self.supply):
            return False
        if (self.bot.supply_workers < self.workers):
            return False
        for unit_type, amount_required, completed in self.requirements:
            unit_count: int = (
                self.bot.structures(unit_type).ready.amount
                + self.bot.units(unit_type).ready.amount
            )
            if (not completed):
                unit_count += self.bot.already_pending(unit_type)
            if (unit_count < amount_required):
                return False
        for upgrade in self.upgrades_required:
            if (self.bot.already_pending_upgrade(upgrade) < 1):
                return False
        return True
    
    def print_check(self) -> None:
        checked_character: str = 'X' if self.checked else ' '
        print(f'[{checked_character}] BO -- {self.name}')



class BuildOrder:
    steps: List[BuildOrderStep]
    name: str

    def __init__(self, bot: BotAI):
        self.bot = bot
    
    # steps not yet completed
    @property
    def unchecked(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if not step.checked]
    
    @property
    def pending_ids(self) -> List[UnitTypeId | UpgradeId]:
        return [step.step_id for step in self.steps if not step.checked and step.can_check]
    
    @property
    def is_completed(self) -> bool:
        return len(self.unchecked) == 0
    
    # steps already completed
    @property
    def completed_steps(self) -> List[BuildOrderStep]:
        return [step for step in self.steps if step.checked]
    
    @property
    def completed_buildings(self) -> dict[UnitTypeId, int]:
        completed: dict[UnitTypeId, int] = {}
        for step in self.completed_steps:
            unit_id: UnitTypeId = step.step_id
            if (unit_id in build_order_structures):
                if (unit_id in completed.keys()):
                    completed[unit_id] += 1
                else:
                    completed[unit_id] = 1
        return completed

    
    # next step to execute
    @property
    def next(self) -> BuildOrderStep | None:
        return next((step for step in self.steps if not step.checked), None)
    
    def check(self, step_id: UnitTypeId) -> bool:
        for step in self.unchecked:
            if (step.step_id == step_id):
                step.checked = True
                step.print_check()
                return True
        return False
    
    def modify_composition(self, composition: Composition) -> None:
        pass