
from typing import List
from bot.army_composition.composition import Composition
from bot.buildings.addon_swap.swap_plan import SwapPlan
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from bot.utils.unit_tags import build_order_structures

class BuildOrderStep:
    bot: BotAI
    step_id: UnitTypeId | UpgradeId
    target_count: int
    workers: int
    supply: int
    army_supply: int
    townhalls: int
    requirements: tuple[UnitTypeId, int, bool]
    upgrades_required: List[UpgradeId]
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
        # UnitTypeId.FACTORYREACTOR: [UnitTypeId.STARPORTREACTOR],
    }
    
    def __init__(
        self,
        bot: BotAI,
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
        
        return self.unit_amount(self.step_id)
    
    def unit_amount(self, unit_id: UnitTypeId, include_pending: bool = True):
        unit_ids: list[UnitTypeId] = [unit_id]

        if (unit_id in self.equivalences.keys()):
            unit_ids.extend(self.equivalences[unit_id])

        # TODO add addons that are swapped
        # for swap in self.bot.current_build.addon_swaps:
        #     if (swap.desired_addon_type == unit_id):
        #         unit_ids.append(swap.donor_type)
        #         if (swap.donor_needs_addon_after_swap):
        #             unit_ids.append(swap.recipient_type)
        
        count: int = (
            self.bot.structures(unit_ids).ready.amount
            + self.bot.units(unit_ids).ready.amount
        )
        if (include_pending):
            count += self.bot.already_pending(unit_id)
        
        return count
    
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
            unit_count: int = self.unit_amount(unit_type, include_pending=not completed)
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
            unit_count: int = self.unit_amount(unit_type, include_pending=not completed)
            if (unit_count < amount_required):
                return False
        for upgrade in self.upgrades_required:
            if (self.bot.already_pending_upgrade(upgrade) < 1):
                return False
        return True
    
    # def print_check(self) -> None:
    #     checked_character: str = 'X' if self.checked else ' '
    #     print(f'[{checked_character}] BO -- {self.name}')



class BuildOrder:
    steps: List[BuildOrderStep]
    name: str
    addon_swaps: List[SwapPlan]

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.addon_swaps = []
    
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