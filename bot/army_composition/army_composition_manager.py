from __future__ import annotations
import math
from typing import List, TYPE_CHECKING
from bot.army_composition.composition import Composition
from bot.strategy.strategy_types import Situation
from bot.utils.army import Army
from bot.utils.matchup import Matchup
from bot.utils.unit_supply import get_unit_supply
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.units import Units
from bot.utils.unit_tags import cloaked_units, burrowed_units

if TYPE_CHECKING:
    from bot import WickedBot  # only imported for type hints

composition_manager: ArmyCompositionManager | None = None

class ArmyCompositionManager:
    bot: BotAI
    composition: Composition

    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.composition = Composition(bot, 0)

    def __is_available(self, unit_upgrade_type: UnitTypeId|UpgradeId) -> bool:
        if (isinstance(unit_upgrade_type, UnitTypeId)):
            return self.bot.structures(unit_upgrade_type).ready.amount >= 1
        else:
            return self.bot.already_pending(unit_upgrade_type) > 0

    @property
    def wicked(self) -> WickedBot:
        return self.bot  # type: ignore

    @property
    def available_units(self) -> List[UnitTypeId]:
        available_units: List[UnitTypeId] = []
        
        unlocks: dict[UnitTypeId, List[UnitTypeId|UpgradeId]] = {
            UnitTypeId.REAPER: [UnitTypeId.BARRACKS],
            UnitTypeId.MARINE: [UnitTypeId.BARRACKS],
            UnitTypeId.MARAUDER: [UnitTypeId.BARRACKSTECHLAB, UnitTypeId.BARRACKS, UpgradeId.STIMPACK],
            UnitTypeId.GHOST: [UnitTypeId.GHOSTACADEMY, UnitTypeId.BARRACKSTECHLAB, UnitTypeId.BARRACKS],
            UnitTypeId.MEDIVAC: [UnitTypeId.STARPORT],
            UnitTypeId.VIKINGFIGHTER: [UnitTypeId.STARPORT],
            UnitTypeId.RAVEN: [UnitTypeId.STARPORTTECHLAB, UnitTypeId.STARPORT],
        }

        for unit_type, requirements in unlocks.items():
            if all(self.__is_available(req) for req in requirements):
                available_units.append(unit_type)
        return available_units
    
    @property
    def vikings_amount(self) -> int:
        # so far we max our viking amount at 36
        max_viking_amount: int = 36

        # we want pretty much matching air supply
        enemy_units: Units = self.wicked.scouting.known_enemy_army.units + self.wicked.enemy_structures
        viking_response: dict[UnitTypeId, int] = {
            UnitTypeId.CARRIER: 4,
            UnitTypeId.COLOSSUS: 4,
            UnitTypeId.BATTLECRUISER: 4,
            UnitTypeId.TEMPEST: 3,
            UnitTypeId.BROODLORD: 3,
            UnitTypeId.MOTHERSHIP: 5,
            UnitTypeId.WARPPRISM: 0.33,
            UnitTypeId.MUTALISK: 0,
            UnitTypeId.OBSERVER: 0,

            # buildings that produce air units
            UnitTypeId.ROBOTICSBAY: 2,
            UnitTypeId.STARGATE: 1,
            UnitTypeId.FLEETBEACON: 2,
            UnitTypeId.GREATERSPIRE: 2,
        }
        viking_amount: float = sum(
            viking_response.get(unit.type_id, get_unit_supply(unit.type_id) / 2 if unit.is_flying else 0)
            for unit in enemy_units
        )

        # round, because 2.3 vikings = 2 vikings in practice
        return min(max_viking_amount, round(viking_amount))
    
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
    
    def default_amount(self, unit_type: UnitTypeId) -> int | bool:
        match unit_type:
            case UnitTypeId.MEDIVAC:
                return 6
            case UnitTypeId.MARINE:
                return 30
            case _:
                return False

    def calculate_composition(self) -> Composition:
        available_units: List[UnitTypeId] = self.available_units
        units: Units = self.wicked.units_with_passengers

        max_army_supply: int = 200 - self.wicked.trainer.scv.max_amount
        composition: Composition = Composition(self.bot, max_army_supply)
        marine_count: int = self.wicked.units(UnitTypeId.MARINE).amount + self.wicked.already_pending(UnitTypeId.MARINE)

        for unit_type in available_units:
            if (self.default_amount(unit_type)):
                composition.set(unit_type, self.default_amount(unit_type))

        
        if (UnitTypeId.VIKINGFIGHTER in available_units):
            composition.add(UnitTypeId.VIKINGFIGHTER, self.vikings_amount)
        
        # only start making marauders once we have at least 8 marines unless we're in danger
        if (UnitTypeId.MARAUDER in available_units and (marine_count >= 8 or self.wicked.scouting.situation == Situation.UNDER_ATTACK)):
            marauder_supply: int = int(composition.supply_remaining * self.marauders_ratio)
            marauder_count: int = marauder_supply // 2
            composition.add(UnitTypeId.MARAUDER, marauder_count)
        
        # always add a minimum of the Ghost we own so far
        ghost_count: int = units(UnitTypeId.GHOST).amount
        composition.add(UnitTypeId.GHOST, ghost_count)
        
        # if we have at least 3 bases and are playing TvZ, we want 1 Raven
        # Also true if we need detection against cloaked/burrowed units
        if (
            self.wicked.structures(UnitTypeId.ORBITALCOMMAND).ready.amount >= 3
            and (
                self.wicked.matchup == Matchup.TvZ 
                or cloaked_units in self.wicked.scouting.known_enemy_composition
                or burrowed_units in self.wicked.scouting.known_enemy_composition
            ) 
        ):
            composition.set(UnitTypeId.RAVEN, 1)
        
        # in early game set our composition to only be 1 reaper
        if (self.bot.time <= 120):
            composition.set(UnitTypeId.REAPER, 1)
            composition.set(UnitTypeId.MARINE, 0)
        else:
            # if we have medivacs and a lot of bio, get the medivac count up to 10
            if (UnitTypeId.MEDIVAC in available_units):
                # add up to 4 Medivac if we already have a lot of bio
                bio_supply: int = (
                    Army(self.wicked.units([UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.GHOST]), self.wicked).supply
                    + self.bot.already_pending(UnitTypeId.MARINE) * 1
                    + self.bot.already_pending(UnitTypeId.MARAUDER) * 2
                    + self.bot.already_pending(UnitTypeId.GHOST) * 3
                )
                if (bio_supply >= 8 * self.default_amount(UnitTypeId.MEDIVAC)):
                    composition.set(UnitTypeId.MEDIVAC, min(10, round(bio_supply / 8)))

            
            # always fill the rest of the composition with 1/2 of Marines
            composition.fill(UnitTypeId.MARINE, 1/2)
            
            # Then, finish with either Ghost or Marines
            if (UnitTypeId.GHOST in self.available_units):
                composition.fill(UnitTypeId.GHOST)
            else:
                composition.fill(UnitTypeId.MARINE)
        
        self.composition = composition

    def get(self, unit_type: UnitTypeId) -> Composition:
        return self.composition[unit_type]

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