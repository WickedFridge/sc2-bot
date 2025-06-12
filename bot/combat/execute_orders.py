from typing import List, Optional
from bot.combat.micro import Micro
from bot.superbot import Superbot
from bot.utils.army import Army
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import worker_types

PICKUP_RANGE: int = 3

class Execute:
    bot: Superbot
    micro: Micro

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.micro = Micro(bot)

    async def drop(self, army: Army):
        # define which base to drop
        # we'll start with the natural
        
        drop_target: Point2 = self.bot.expansions.enemy_b2.position
        closest_center: Point2 = self.bot.map.closest_center(drop_target)
        
        medivacs: Units = army.units(UnitTypeId.MEDIVAC)
        
        # select dropping medivacs
        usable_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left >= 1 and unit.health_percentage >= 0.4)
        full_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left == 0)
        
        if ((usable_medivacs + full_medivacs).amount > 2):
            sorted_usable_medivacs: Units = usable_medivacs.sorted(lambda unit: (-unit.health, unit.tag))
            droppable_medivac: Units = sorted_usable_medivacs.take(max(0, usable_medivacs.amount - full_medivacs.amount))
        else:
            droppable_medivac: Units = usable_medivacs
        ground_units: Units = army.units.filter(lambda unit: unit.is_flying == False)
        await self.pickup(droppable_medivac, ground_units)
        dropping_medivac: Units = droppable_medivac + full_medivacs if army.ground_units.amount == 0 else full_medivacs
        
        for medivac in dropping_medivac:
            distance_medivac_to_target = medivac.position.distance_to(drop_target)
            distance_edge_to_target = closest_center.distance_to(drop_target)
            
            # If the edge is closer to the target than we are, take the detour
            if (distance_edge_to_target < distance_medivac_to_target):
                # Optional: Only go to edge if not already very close to it
                if medivac.position.distance_to(closest_center) > 5:
                    medivac.move(closest_center)
                else:
                    medivac.move(drop_target)
            else:
                # Direct path is better
                medivac.move(drop_target)

    async def pickup(self, medivacs: Units, ground_units: Units):
        # units get closer to medivacs
        for unit in ground_units:
            if (medivacs.amount == 0):
                self.micro.retreat(unit)
                break
            unit.move(medivacs.closest_to(unit))
        
        # medivacs boost and pickup
        for medivac in medivacs:
            await self.micro.medivac_pickup(medivac, ground_units)


    async def pickup_leave(self, army: Army):
        ground_units: Units = army.units.filter(lambda unit: unit.is_flying == False)
        if (army.center.distance_to(self.micro.retreat_position) <= 20 or ground_units.amount == 0):
            self.retreat_army(army)
            return
        medivacs: Units = army.units(UnitTypeId.MEDIVAC)
        usable_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left >= 1 and unit.health_percentage >= 0.4)
        retreating_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left == 0 or unit.health_percentage < 0.4)
        await self.pickup(usable_medivacs, ground_units)
        for medivac in retreating_medivacs:
            self.micro.retreat(medivac)

    async def heal_up(self, army: Army):
        # drop units
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                if (not unit.is_using_ability(AbilityId.UNLOADALLAT_MEDIVAC)):
                    unit(AbilityId.UNLOADALLAT_MEDIVAC, unit)
                await self.micro.medivac_fight(unit, army.units)
            # group units that aren't near the center
            else:
                if (unit.distance_to(army.center) > 5):
                    unit.move(army.center)
    
    def retreat_army(self, army: Army):
        for unit in army.units:
            self.micro.retreat(unit)

    async def fight(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight(unit, army.units)
                case UnitTypeId.MARINE:
                    self.micro.bio(unit)
                case UnitTypeId.MARAUDER:
                    self.micro.bio(unit)
                case _:
                    closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                    unit.attack(closest_enemy_unit)

    async def fight_defense(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight(unit, army.units)
                case UnitTypeId.MARINE:
                    self.micro.bio_defense(unit)
                case UnitTypeId.MARAUDER:
                    self.micro.bio_defense(unit)
                case _:
                    closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                    unit.attack(closest_enemy_unit)

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
        enemy_bunkers: Units = self.bot.enemy_structures(UnitTypeId.BUNKER).filter(
            lambda unit: (
                unit.distance_to(army.units.center) <= 30
            )
        )
        enemy_bunkers_completed: Units = enemy_bunkers.ready
        enemy_bunkers_in_progress: Units = enemy_bunkers.filter(lambda unit: unit.build_progress < 1)
        ally_bunkers: Units = self.bot.units(UnitTypeId.BUNKER).ready
        enemy_marines: Units = self.bot.enemy_units(UnitTypeId.MARINE).filter(lambda unit: unit.distance_to(army.units.center) <= 20)
        enemy_reapers: Units = self.bot.enemy_units(UnitTypeId.REAPER).filter(lambda unit: unit.distance_to(army.units.center) <= 20)
        scvs_building: Units = (
            Units([], self.bot) if enemy_bunkers_in_progress.amount == 0
            else self.bot.enemy_units(UnitTypeId.SCV).filter(lambda unit: enemy_bunkers_in_progress.closest_distance_to(unit) <= 3)
        )

        # focus the building SCVs first
        for unit in army.units:
            if (scvs_building.amount):
                closest_scv_building: Unit = scvs_building.closest_to(unit)
                
                # if we have a completed bunker in range, hop in
                if (ally_bunkers.amount >= 1):
                    closest_ally_bunker: Unit = ally_bunkers.closest_to(closest_scv_building)
                    if (closest_ally_bunker.distance_to(closest_scv_building) < 7):
                        unit.move(closest_ally_bunker)
                        closest_ally_bunker(AbilityId.LOAD_BUNKER, unit)
                        break

                # if we are on cooldown, find the best target and shoot at it
                closest_enemy_bunker_in_progress: Unit = enemy_bunkers_in_progress.closest_to(unit)
                if (unit.weapon_cooldown == 0):
                    target: Unit = self.find_bunker_rush_target(
                        unit,
                        closest_scv_building,
                        closest_enemy_bunker_in_progress,
                        enemy_marines,
                        enemy_reapers
                    )
                    if (target):
                        unit.attack(target)
                        break

            # otherwise identify menacing bunkers and attack the scv building them
            menacing_bunkers: Units = enemy_bunkers_in_progress.in_distance_of_group(self.bot.townhalls, 7)
            if (self.handle_enemy_bunkers(unit, ally_bunkers, menacing_bunkers)):
                break

            # if enemy has terrifying bunkers completed, not sure what to do yet
            terrifying_bunkers: Units = enemy_bunkers_completed.in_distance_of_group(self.bot.townhalls, 7)
            if (self.handle_enemy_bunkers(unit, ally_bunkers, terrifying_bunkers)):
                break
            
            #print not sure here
            print("Warning, not sure how to defend !")
    
    def handle_enemy_bunkers(self, unit: Unit, bunkers: Units, menacing_bunkers: Units) -> bool:
        if (menacing_bunkers.amount >= 1):
            if (bunkers.amount >= 1):
                closest_ally_bunker: Unit = bunkers.closest_to(menacing_bunkers)
                if (menacing_bunkers.closest_distance_to(closest_ally_bunker) <= 7):
                    unit.move(closest_ally_bunker)
                    closest_ally_bunker(AbilityId.LOAD_BUNKER, unit)
                    return True
            menacing_bunkers_in_range: Units = menacing_bunkers.in_attack_range_of(unit)
            if (menacing_bunkers_in_range.amount == 0):
                unit.attack(menacing_bunkers.closest_to(unit))
                return True
            unit.attack(menacing_bunkers_in_range.sorted(lambda bunker: bunker.health).first)
            return True
        return False

    def find_bunker_rush_target(self, unit: Unit, closest_scv_building: Unit, closest_enemy_bunker_in_progress: Unit, enemy_marines: Units, enemy_reapers: Units) -> Optional[Unit]:
        if (unit.target_in_range(closest_scv_building)):
            return closest_scv_building
        if (unit.target_in_range(closest_enemy_bunker_in_progress)):
            return closest_enemy_bunker_in_progress
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
                unit.distance_to(army.center) <= 30
            )
        )
        if (canons.amount == 0):
            print("Error : no canons detected")
            return

        #TODO improve this
        canons.sort(key=lambda unit: (unit.health + unit.shield, unit.distance_to(self.bot.expansions.main.position)))
        for unit in army.units:
            unit.attack(canons.first)

    async def harass(self, army: Army):
        enemy_workers_close: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.distance_to(army.units.center) <= 20
                and unit.can_be_attacked
                and unit.type_id in worker_types
            )
        )
        if (enemy_workers_close.amount == 0):
            print("Error: no worker close")
            return
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
            else:
                unit.attack(enemy_workers_close.closest_to(unit))
    
    async def kill_buildings(self, army: Army):
        local_enemy_buildings: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.distance_to(army.units.center) <= 10 and unit.can_be_attacked
        )
        local_enemy_buildings.sort(key=lambda building: building.health)
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
            else:
                unit.attack(local_enemy_buildings.first)

    async def attack_nearest_base(self, army: Army):
        # if army is purely air
        if (not army.leader):
            return
        nearest_base_target: Point2 = self.micro.get_nearest_base_target(army.leader)
        self.micro.attack_position(army.leader, nearest_base_target)
        for unit in army.followers:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
            else:
                if (unit.position.distance_to(army.leader.position) >= 3):
                    unit.move(army.leader.position)
        
    async def chase_buildings(self, army: Army):
        # if army is purely air
        if (not army.leader):
            return
        attack_position: Point2 = self.bot.enemy_structures.closest_to(army.leader).position
        self.micro.attack_position(army.leader, attack_position)
        for unit in army.followers:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
            else:
                unit.move(army.leader.position)

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