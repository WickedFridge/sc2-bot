from typing import List
from bot.combat.micro import Micro
from bot.utils.army import Army
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, hq_types, menacing


class Execute:
    bot: BotAI
    micro: Micro

    def __init__(self, bot) -> None:
        self.bot = bot
        self.micro = Micro(bot)

    def retreat_army(self, army: Army):
        for unit in army.units:
            self.micro.retreat(unit)

    async def fight(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac(unit, army.units)
                case UnitTypeId.MARINE:
                    self.micro.bio(unit)
                case UnitTypeId.MARAUDER:
                    self.micro.bio(unit)
                case _:
                    closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                    unit.attack(closest_enemy_unit)

    async def attack_nearest_base(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac(unit, army.units)
                case _:
                    self.micro.attack_nearest_base(unit)

    def defend(self, army: Army):
        main_position: Point2 = self.bot.start_location
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        enemy_units_attacking: Units = self.bot.enemy_units.filter(
            lambda unit: unit.distance_to(main_position) < unit.distance_to(enemy_main_position)
        )
        for unit in army.units:
            if (enemy_units_attacking.amount >= 1):
                unit.attack(enemy_units_attacking.closest_to(unit))
            else:
                # TODO: Handle defense when we took a base on the opponent's half of the map
                print("Error : no threats to defend from")

    async def harass(self, army: Army):
        enemy_workers_close: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.distance_to(army.units.center) <= 30
                and unit.can_be_attacked
                and unit.type_id in worker_types
            )
        )
        if (enemy_workers_close.amount == 0):
            print("Error: no worker close")
            return
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac(unit, army.units)
            else:
                unit.attack(enemy_workers_close.closest_to(unit))
    
    async def kill_buildings(self, army: Army):
        local_enemy_buildings: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.distance_to(army.units.center) <= 10 and unit.can_be_attacked
        )
        local_enemy_buildings.sort(key=lambda building: building.health)
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac(unit, army.units)
            else:
                unit.attack(local_enemy_buildings.first)

    async def chase_buildings(self, army: Army):
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac(unit, army.units)
            else:
                unit.attack(self.bot.enemy_structures.closest_to(unit))

    def regroup(self, army: Army, armies: List[Army]):
        other_armies = list(filter(lambda other_army: other_army.center != army.center, armies))
        if (other_armies.__len__() == 0):
            return
        closest_army_position: Point2 = other_armies[0].center
        for other_army in other_armies:
            if (army.center.distance_to(other_army.center) < army.center.distance_to(closest_army_position)):
                closest_army_position = other_army.center
        for unit in army.units:
            unit.move(closest_army_position)