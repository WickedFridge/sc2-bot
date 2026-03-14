from typing import List

from attr import dataclass
from bot.army_composition.army_composition_manager import ArmyCompositionManager
from bot.strategy.build_order.addon_swap import AddonSwapManager
from bot.macro.expansion_manager import Expansions
from bot.macro.map.map import MapData
from bot.scouting.ghost_units.manager import GhostUnitsManager
from bot.scouting.scouting import Scouting
from bot.strategy.build_order.manager import BuildOrderManager
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI
from sc2.cache import property_cache_once_per_frame
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units

class Superbot(BotAI):
    addon_swap: AddonSwapManager
    
    @property
    def matchup(self) -> Matchup:
        pass
    
    @property
    def expansions(self) -> Expansions:
        pass
    
    @property
    def map(self) -> MapData:
        pass

    @property
    def scouting(self) -> Scouting:
        pass
    
    @property
    def composition_manager(self) -> ArmyCompositionManager:
        pass

    @property
    def build_order(self) -> BuildOrderManager:
        pass

    @property
    def ghost_units(self) -> GhostUnitsManager:
        pass

    @property
    def orbital_tech_available(self) -> bool:
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9
    
    
    @property_cache_once_per_frame
    def units_with_passengers(self) -> Units:
        units: Units = self.units.copy()
        if (units.amount == 0):
            return units
        for medivac in units(UnitTypeId.MEDIVAC):
            if (medivac.has_cargo):
                for passenger in medivac.passengers:
                    units.append(passenger)
        return units
    
    def equivalences(self, unit_type: UnitTypeId) -> List[UnitTypeId]:
        match (unit_type):
            case UnitTypeId.THOR | UnitTypeId.THORAP:
                return [UnitTypeId.THOR, UnitTypeId.THORAP]
            case UnitTypeId.HELLION | UnitTypeId.HELLIONTANK:
                return [UnitTypeId.HELLION, UnitTypeId.HELLIONTANK]
            case UnitTypeId.VIKINGFIGHTER | UnitTypeId.VIKINGASSAULT:
                return [UnitTypeId.VIKINGFIGHTER, UnitTypeId.VIKINGASSAULT]
            case UnitTypeId.SIEGETANK | UnitTypeId.SIEGETANKSIEGED:
                return [UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED]            
            case _:
                return [unit_type]

    def total_unit_amount(self, unit_type: UnitTypeId) -> int:
        unit_types: List[UnitTypeId] = self.equivalences(unit_type)
        # return sum(self.units_with_passengers(u_type).amount + self.already_pending(u_type) for u_type in unit_types)
        total_amount: int = self.units_with_passengers(unit_types).amount
        for u_type in unit_types:
            total_amount += self.already_pending(u_type)
        return total_amount