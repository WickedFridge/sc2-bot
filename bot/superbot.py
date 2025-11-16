from bot.army_composition.army_composition_manager import ArmyCompositionManager
from bot.macro.expansion_manager import Expansions
from bot.macro.map.map import MapData
from bot.scouting.scouting import Scouting
from bot.strategy.build_order.manager import BuildOrderManager
from bot.utils.matchup import Matchup
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Superbot(BotAI):
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
    def orbital_tech_available(self) -> bool:
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9
    
    
    @property
    def units_with_passengers(self) -> Units:
        units: Units = self.units.copy()
        if (units.amount == 0):
            return units
        for medivac in units(UnitTypeId.MEDIVAC):
            if (medivac.has_cargo):
                for passenger in medivac.passengers:
                    units.append(passenger)
        return units
    
    def total_unit_amount(self, unit_type: UnitTypeId) -> int:
        return self.units_with_passengers(unit_type).amount + self.already_pending(unit_type)