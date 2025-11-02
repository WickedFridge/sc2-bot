from typing import Dict, Iterator, List
from bot.utils.colors import GREEN, RED, WHITE
from bot.utils.unit_supply import get_unit_supply
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
    
class  Composition:
    bot: BotAI
    supply_cap: int
    units: Dict[UnitTypeId, int]

    def __init__(self, bot: BotAI, supply_cap: int) -> None:
        self.bot = bot
        self.supply_cap = supply_cap
        self.units = {}
    
    def add(self, unit_type: UnitTypeId, count: int = 1) -> None:
        """Add units of a given type to the composition."""
        if (count == 0):
            return
        self.units[unit_type] = self.units.get(unit_type, 0) + count
    
    def set(self, unit_type: UnitTypeId, count: int = 1) -> None:
        """Add units of a given type to the composition."""
        self.units[unit_type] = count

    def remove(self, unit_type: UnitTypeId, count: int = 1) -> None:
        """Remove units, dropping to zero if count exceeds."""
        if (count == 0):
            return
        if (unit_type in self.units):
            self.units[unit_type] = max(0, self.units[unit_type] - count)
            if (self.units[unit_type] == 0):
                del self.units[unit_type]

    @property
    def total_supply(self) -> int:
        """Total supply used by this composition."""
        return sum(get_unit_supply(unit) * count for unit, count in self.units.items())

    @property
    def supply_remaining(self) -> int:
        """How much supply is left before hitting cap."""
        return self.supply_cap - self.total_supply

    @property
    def keys(self) -> List[UnitTypeId]:
        return list(self.units.keys())
    
    def __getitem__(self, unit_type: UnitTypeId) -> int:
        return self.units.get(unit_type, 0)

    def __setitem__(self, unit_type: UnitTypeId, count: int) -> None:
        self.units[unit_type] = count

    def __iter__(self) -> Iterator[UnitTypeId]:
        return iter(self.units)

    def __repr__(self) -> str:
        output: str = f'Supply cap: {self.supply_cap}\n'
        for unit_type, count in self.units.items():
            output += f'{unit_type.name}: {count}\n'
        return output
    
    @property
    def debug_info(self) -> List[tuple[str, tuple[int, int, int]]]:
        output: List[tuple[str, tuple[int, int, int]]] = [(f'Supply cap: {self.supply_cap}', WHITE)]
        all_units: Units = self.bot.units.copy()
        if (all_units.amount == 0):
            return all_units
        for medivac in all_units(UnitTypeId.MEDIVAC):
            if (medivac.has_cargo):
                for passenger in medivac.passengers:
                    all_units.append(passenger)
        
        for unit_type, count in self.units.items():
            current_count: int = all_units(unit_type).amount + self.bot.already_pending(unit_type)
            color = WHITE
            if (current_count == count):
                color = GREEN
            elif (current_count > count):
                color = RED
            output.append((f'{current_count}/{count} : {unit_type.name}', color))
        return output
    
    def fill(self, unit_type: UnitTypeId, ratio: float = 1) -> None:
        """Fill remaining supply with a specific unit type."""
        unit_supply_value: int = get_unit_supply(unit_type)
        max_addable: int = self.supply_remaining // unit_supply_value
        if (max_addable >= 1):
            self.add(unit_type, int(max_addable * ratio))