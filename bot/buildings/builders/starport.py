from typing import List, override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class Starport(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.STARPORT
        self.unitIdFlying = UnitTypeId.STARPORTFLYING
        self.name = "Starport"
    
    @override
    @property
    def custom_conditions(self) -> bool:
        if (self.bot.build_order.build.is_completed == False):
            return True
        
        ebays_amount: int = self.bot.structures(UnitTypeId.ENGINEERINGBAY).amount
        flying_unit_types: List[UnitTypeId] = [
            UnitTypeId.MEDIVAC,
            UnitTypeId.VIKINGFIGHTER,
            UnitTypeId.RAVEN,
            UnitTypeId.BANSHEE,
            UnitTypeId.BATTLECRUISER
        ]
        flying_units_amount: int = self.bot.units(flying_unit_types).amount
        for unit_type in flying_unit_types:
            flying_units_amount += self.bot.already_pending(unit_type)

        # We want 2nd/3rd starport after we have a 3rd base and 2 Ebays if our composition is mostly air units
        match self.amount:
            case 0:
                return True
            case 1|2: 
                return (
                    self.base_amount >= 3
                    and ebays_amount >= 2
                    and flying_units_amount >= 2
                    and (
                        self.bot.composition_manager.vikings_amount >= 4 * self.amount
                        or self.bot.composition_manager.amount_to_train(UnitTypeId.RAVEN) >= self.amount
                    )
                )
            case _:
                return False
            
    @override
    @property
    def position(self) -> Point2:
        if (self.bot.build_order.build.name in ['Defensive Cyclone']):
            return self.bot.expansions.main.position.towards(self.bot.game_info.map_center, 4)
        factories: Units = self.bot.structures(UnitTypeId.FACTORY).ready + self.bot.structures(UnitTypeId.FACTORYFLYING)
        factory_position: Point2 = factories.first.position
        # if (self.bot.game_info.map_center.y > factory_position.y):
        #     return factory_position + Point2((0, 2.5))
        # return factory_position + Point2((0, -2.5))
        return factory_position.towards(self.bot.game_info.map_center, 2)