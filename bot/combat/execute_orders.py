from typing import List, Optional
from bot.combat.micro import Micro
from bot.utils.army import Army
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
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
    
    def defend_bunker_rush(self, army: Army):
        bunkers: Units = self.bot.enemy_structures(UnitTypeId.BUNKER).filter(
            lambda unit: (
                unit.distance_to(army.units.center <= 30)
            )
        )
        enemy_bunkers_completed: Units = bunkers.ready
        enemy_bunkers_in_progress: Units = bunkers.filter(lambda unit: unit.build_progress < 1)
        bunkers: Units = self.bot.units(UnitTypeId.BUNKER).ready
        enemy_marines: Units = self.bot.enemy_units(UnitTypeId.MARINE).filter(lambda unit: unit.distance_to(army.units.center <= 20))
        enemy_reapers: Units = self.bot.enemy_units(UnitTypeId.REAPER).filter(lambda unit: unit.distance_to(army.units.center <= 20))
        scvs_building: Units = self.bot.enemy_units(UnitTypeId.SCV).filter(lambda unit: bunkers.closest_distance_to(unit) <= 3)

        # focus the building SCVs first
        for unit in army.units:
            if (scvs_building.amount):
                closest_scv_building: Unit = scvs_building.closest_to(unit)
                closest_bunker: Unit = bunkers.closest_to(closest_scv_building)
                
                # if we have a completed bunker in range, hop in
                if (closest_bunker.distance_to(closest_scv_building) < 7):
                    unit.move(closest_bunker)
                    closest_bunker(AbilityId.LOAD_BUNKER, unit)
                    break

                # if we are on cooldown, find the best target and shoot at it
                if (unit.weapon_cooldown == 0):
                    target: Unit = self.find_bunker_rush_target(
                        unit,
                        closest_scv_building,
                        closest_bunker,
                        enemy_marines,
                        enemy_reapers
                    )
                    if (target):
                        unit.attack(target)
                        break

            # otherwise identify menacing bunkers and attack the scv building them
            menacing_bunkers: Units = enemy_bunkers_in_progress.in_distance_of_group(self.bot.townhalls, 7)
            if (self.handle_enemy_bunkers(unit, bunkers, menacing_bunkers)):
                break

            # if enemy has terrifying bunkers completed, not sure what to do yet
            terrifying_bunkers: Units = enemy_bunkers_completed.in_distance_of_group(self.bot.townhalls, 7)
            if (self.handle_enemy_bunkers(unit, bunkers, terrifying_bunkers)):
                break
            
            #print not sure here
            print("Warning, not sure how to defend !")
    
    def handle_enemy_bunkers(self, unit: Unit, bunkers: Units, menacing_bunkers: Units) -> bool:
        closest_ally_bunker: Unit = bunkers.closest_to(menacing_bunkers)
        if (menacing_bunkers.amount >= 1):
            if (menacing_bunkers.closest_distance_to(closest_ally_bunker) <= 7):
                unit.move(closest_ally_bunker)
                closest_ally_bunker(AbilityId.LOAD_BUNKER, unit)
                return True
            unit.attack(menacing_bunkers)
            return True
        return False

    def find_bunker_rush_target(self, unit: Unit, closest_scv_building: Unit, closest_bunker: Unit, enemy_marines: Units, enemy_reapers: Units) -> Optional[Unit]:
        if (unit.target_in_range(closest_scv_building)):
            return closest_scv_building
        if (unit.target_in_range(closest_bunker)):
            return closest_bunker
        marines_in_range: Units = enemy_marines.filter(lambda enemy: unit.target_in_range(enemy))
        marines_in_range.sorted(lambda unit: unit.health)
        if (marines_in_range.amount):
            return marines_in_range.first
        reapers_in_range: Units = enemy_reapers.filter(lambda enemy: unit.target_in_range(enemy))
        reapers_in_range.sorted(lambda unit: unit.health)
        if (reapers_in_range.amount):
            return reapers_in_range.first
        return None

    def defend_canon_rush(self, army: Army):
        canons: Units = self.bot.enemy_structures(UnitTypeId.PHOTONCANNON).filter(
            lambda unit: (
                unit.distance_to(army.units.center <= 30)
            )
        )
        #TODO improve this
        canons.sort(key=lambda unit: (unit.health + unit.shield, unit.distance_to(self.bot.start_location)))
        for unit in army:
            unit.attack(canons.first)

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