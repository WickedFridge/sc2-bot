from __future__ import annotations
import math
from typing import List, TYPE_CHECKING
from bot.army_composition.composition import Composition
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from bot.utils.unit_supply import supply

if TYPE_CHECKING:
    from bot import WickedBot  # only imported for type hints

composition_manager: ArmyCompositionManager | None = None

class ArmyCompositionManager:
    bot: BotAI
    composition: Composition

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.composition = Composition(bot, 0)

    def __is_available(self, unit_type: UnitTypeId) -> bool:
        return self.bot.structures(unit_type).ready.amount >= 1

    @property
    def wicked(self) -> WickedBot:
        return self.bot  # type: ignore

    @property
    def available_units(self) -> List[UnitTypeId]:
        available_units: List[UnitTypeId] = []
        
        unlocks: dict[UnitTypeId, List[UnitTypeId]] = {
            UnitTypeId.REAPER: [UnitTypeId.BARRACKS],
            UnitTypeId.MARINE: [UnitTypeId.BARRACKS],
            UnitTypeId.MARAUDER: [UnitTypeId.BARRACKSTECHLAB, UnitTypeId.BARRACKS],
            UnitTypeId.GHOST: [UnitTypeId.GHOSTACADEMY, UnitTypeId.BARRACKSTECHLAB, UnitTypeId.BARRACKS],
            UnitTypeId.MEDIVAC: [UnitTypeId.STARPORT],
            UnitTypeId.VIKINGFIGHTER: [UnitTypeId.STARPORT],
        }

        for unit_type, requirements in unlocks.items():
            if all(self.__is_available(req) for req in requirements):
                available_units.append(unit_type)
        return available_units
    
    @property
    def vikings_amount(self) -> int:
        # we want pretty much matching air supply
        enemy_units: Units = self.wicked.scouting.known_enemy_army.units
        viking_response: dict[UnitTypeId, int] = {
            UnitTypeId.CARRIER: 4,
            UnitTypeId.COLOSSUS: 4,
            UnitTypeId.BATTLECRUISER: 4,
            UnitTypeId.TEMPEST: 3,
            UnitTypeId.BROODLORD: 3,
            UnitTypeId.MOTHERSHIP: 5,
            UnitTypeId.WARPPRISM: 1,
            UnitTypeId.MUTALISK: 0,
        }
        viking_amount: float = sum(
            viking_response.get(unit.type_id, supply[unit.type_id] / 2 if unit.is_flying else 0)
            for unit in enemy_units
        )

        # round up, because 2.3 vikings = 3 vikings in practice
        return int(math.ceil(viking_amount))
        
        # viking_amount: int = self.wicked.scouting.known_enemy_army.flying_fighting_supply // 2
        
        # # we want 4 vikings by colossus
        # colossus_amount: int = self.wicked.scouting.known_enemy_army.fighting_units(UnitTypeId.COLOSSUS).amount
        # viking_amount += 4 * colossus_amount
        
        # # we want 3 more vikings by carrier
        # carrier_amount: int = self.wicked.scouting.known_enemy_army.fighting_units(UnitTypeId.CARRIER).amount
        # viking_amount += 3 * carrier_amount
        # return viking_amount
    
    @property
    def marauders_ratio(self) -> float:
        default_marauder_ratio: dict[Matchup, float] = {
            Matchup.TvT: 0,
            Matchup.TvZ: 0.1,
            Matchup.TvP: 0.3,
            Matchup.TvR: 0.2,
        }
        if (self.wicked.scouting.known_enemy_army.supply < 10):
            return default_marauder_ratio[self.wicked.matchup]
        return max(0.1, self.wicked.scouting.known_enemy_army.armored_ground_supply / self.wicked.scouting.known_enemy_army.supply)
    
    def maximal_amount(self, unit_type: UnitTypeId) -> int | bool:
        match unit_type:
            case UnitTypeId.MEDIVAC:
                return 10
            case UnitTypeId.REAPER:
                return 1
            case _:
                return False

    def calculate_composition(self) -> Composition:
        available_units: List[UnitTypeId] = self.available_units
        units: Units = self.wicked.units_with_passengers

        max_army_supply: int = 200 - self.wicked.trainer.scv.max_amount
        composition: Composition = Composition(self.bot, max_army_supply)

        for unit_type in available_units:
            if (self.maximal_amount(unit_type)):
                composition.set(unit_type, self.maximal_amount(unit_type))

        
        if (UnitTypeId.VIKINGFIGHTER in available_units):
            composition.add(UnitTypeId.VIKINGFIGHTER, self.vikings_amount)
        
        if (UnitTypeId.MARAUDER in available_units):
            # current_marauder_count: int = units(UnitTypeId.MARAUDER).amount
            marauder_supply: int = int(composition.supply_remaining * self.marauders_ratio)
            marauder_count: int = marauder_supply // 2
            # composition.set(UnitTypeId.MARAUDER, max(marauder_count, current_marauder_count))
            composition.add(UnitTypeId.MARAUDER, marauder_count)
        
        # always add a minimum of the Ghost we own so far
        ghost_count: int = units(UnitTypeId.GHOST).amount
        composition.add(UnitTypeId.GHOST, ghost_count)
        
        if (self.bot.time >= 120):
            composition.remove(UnitTypeId.REAPER)
            # always fill the rest of the composition with half Marines
            composition.fill(UnitTypeId.MARINE, 1/2)
            
            # Then, finish with either Ghost or Marines
            if (UnitTypeId.GHOST in self.available_units):
                composition.fill(UnitTypeId.GHOST)
            else:
                composition.fill(UnitTypeId.MARINE)
        self.composition = composition

    def should_train(self, unit_type: UnitTypeId) -> bool:
        return self.amount_to_train(unit_type) >= 1
    
    def amount_to_train(self, unit_type: UnitTypeId) -> int:
        if (unit_type not in self.available_units):
            return 0
        
        unit_type_amount: int = self.wicked.total_unit_amount(unit_type)
        return max(0, self.composition[unit_type] - unit_type_amount)
    
    def ratio_trained(self, unit_type: UnitTypeId) -> float:
        if (unit_type not in self.available_units or self.composition[unit_type] == 0):
            return 1
        unit_type_amount: int = self.wicked.total_unit_amount(unit_type)
        return min(1, unit_type_amount / self.composition[unit_type])

def get_composition_manager(bot: BotAI) -> ArmyCompositionManager:
    global composition_manager
    if (composition_manager is None):
        composition_manager = ArmyCompositionManager(bot)
    return composition_manager