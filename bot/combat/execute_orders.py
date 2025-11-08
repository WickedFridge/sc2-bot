from typing import List, Optional
from bot.combat.micro import Micro
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.point2_functions import center
from bot.utils.unit_supply import get_unit_supply
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import worker_types, building_priorities

PICKUP_RANGE: int = 3

class Execute:
    bot: Superbot
    micro: Micro
    _drop_target: Point2
    _last_calculated_drop_target_time: float = 0

    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.micro = Micro(bot)
        self._drop_target = Point2((5,5))

    @property
    def default_drop_target(self) -> Point2:
        # switch default drop target every 60 seconds
        index_base_to_hit = round(self.bot.time / 60) % 2
        match (index_base_to_hit):
            case 0:
                # print("dropping main")
                return self.bot.expansions.enemy_main.mineral_line
            case 1:
                # print("dropping natural")
                return self.bot.expansions.enemy_b2.mineral_line

    @property
    def drop_target(self) -> Point2:
        # Recalculate drop target only every 2 seconds
        if (self.bot.time - self._last_calculated_drop_target_time >= 2):
            self._drop_target = self.calculate_drop_target()
            self._last_calculated_drop_target_time = self.bot.time
        return self._drop_target
    
    def calculate_drop_target(self) -> Point2:
        # if we don't know about enemy army or enemy bases, drop on the default target
        if (self.bot.expansions.potential_enemy_bases.amount == 0):
            return self.default_drop_target
        
        # otherwise drop on the furthest base from the enemy army if there's an army
        # otherwise drop on the furthest base from our last base
        furthest_point: Point2 = (
            self.bot.scouting.known_enemy_army.center
            if self.bot.scouting.known_enemy_army.units.amount >= 1
            else self.bot.expansions.taken.last.position
        )
        
        sorted_enemy_bases: Expansions = self.bot.expansions.potential_enemy_bases.sorted(
            lambda base: base.position._distance_squared(furthest_point),
            reverse=True,
        )
        return sorted_enemy_bases.first.mineral_line
    
    @property
    def best_edge(self) -> Point2:
        if (self.bot.scouting.known_enemy_army.units.amount == 0):
            return self.bot.map.closest_center(self.drop_target)
        closest_two_centers: List[Point2] = self.bot.map.closest_centers(self.drop_target, 2)
        closest_two_centers.sort(key=lambda center: center._distance_squared(self.bot.scouting.known_enemy_army.center), reverse= True)
        return closest_two_centers[0]

    async def drop(self, army: Army):
        # get the 2 closest edge of the map to the drop target
        # take the furthest one from the enemy army
        medivacs: Units = army.units(UnitTypeId.MEDIVAC)
        
        # select dropping medivacs
        usable_medivacs: Units = medivacs.filter(lambda unit: unit.health_percentage >= 0.4)

        if (usable_medivacs.amount == 0):
            print("Error: no usable medivacs for drop")
            return
        
        # Step 1: Select the 2 fullest Medivacs among the healthy ones
        medivacs_to_use: Units = usable_medivacs.sorted(lambda unit: (unit.health_percentage >= 0.75, unit.cargo_used, unit.health, unit.tag), True).take(2)

        # Step 2: Split the medivacs
        medivacs_to_retreat = medivacs.filter(lambda unit: unit.tag not in medivacs_to_use.tags)
        
        # Step 3: Unload and retreat extras
        for medivac in medivacs_to_retreat:
            if medivac.passengers:
                await self.micro.medivac_unload(medivac)
            await self.micro.retreat(medivac)
        
        # Step 4: Check if the best two are full or need more units (don't drop ghosts)
        ground_units: Units = army.units.filter(lambda unit: unit.is_flying == False)
        cargo_left: int = sum(medivac.cargo_left for medivac in medivacs_to_use)
        pickable_ground_units: Units = ground_units.filter(lambda unit: unit.type_id != UnitTypeId.GHOST and get_unit_supply(unit.type_id) <= cargo_left)
        
        # Step 5: Select the ground units to pickup and retreat with the rest
        if (pickable_ground_units.amount >= 1):
            await self.pickup(medivacs_to_use, pickable_ground_units)
            return
        else:
            for unit in ground_units:
                await self.micro.retreat(unit)
        
        # Step 6 : Drop with the medivacs
        for medivac in medivacs_to_use:
            distance_medivac_to_target = medivac.position.distance_to(self.drop_target)
            distance_edge_to_target = self.best_edge.distance_to(self.drop_target)
            
            # If the edge is closer to the target than we are, take the detour
            if (distance_edge_to_target < distance_medivac_to_target):
                # Optional: Only go to edge if not already very close to it
                if medivac.position.distance_to(self.best_edge) > 5:
                    await self.micro.medivac_boost(medivac)
                    medivac.move(self.best_edge)
                else:
                    medivac.move(self.drop_target)
            else:
                # Direct path is better
                medivac.move(self.drop_target)

    async def pickup(self, medivacs: Units, ground_units: Units):
        # units get closer to medivacs
        for unit in ground_units:
            if (medivacs.amount == 0):
                await self.micro.retreat(unit)
                break
            unit.move(medivacs.closest_to(unit))
        
        # medivacs boost and pickup
        for medivac in medivacs:
            await self.micro.medivac_pickup(medivac, ground_units)


    async def pickup_leave(self, army: Army):
        # First retreat if we're only flying units
        ground_units: Units = army.units.not_flying
        if (army.center.distance_to(self.micro.retreat_position) <= 20 or ground_units.amount == 0):
            await self.retreat_army(army)
            return
        
        # then pickup units
        minimum_cargo_slot: int = 1 if ground_units(UnitTypeId.MARINE).amount >= 1 else 2
        medivacs: Units = army.units(UnitTypeId.MEDIVAC)
        usable_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left >= 1 and unit.health_percentage >= 0.4)
        retreating_medivacs: Units = medivacs.filter(lambda unit: unit.cargo_left < minimum_cargo_slot or unit.health_percentage < 0.4)
        await self.pickup(usable_medivacs, ground_units)
        for medivac in retreating_medivacs:
            menacing_enemy_units: Units = self.bot.enemy_units.filter(
                lambda unit: unit.can_attack_air and unit.distance_to(medivac) <= unit.air_range + 2 
            )
            if (menacing_enemy_units.amount >= 1):
                Micro.move_away(medivac, menacing_enemy_units.center, 5)
            else:
                await self.micro.retreat(medivac)

        other_flying_units: Units = army.units.flying.filter(lambda unit: unit.type_id != UnitTypeId.MEDIVAC)
        await self.retreat_army(Army(other_flying_units, self.bot))

    async def heal_up(self, army: Army):
        # drop units
        for unit in army.units:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_unload(unit)
                self.micro.medivac_heal(unit, army.units)
            if (unit.type_id == UnitTypeId.REAPER):
                await self.micro.retreat(unit)
            # group units that aren't near the center
            else:
                if (unit.distance_to(army.center) > 5):
                    unit.move(army.center)
    
    async def retreat_army(self, army: Army):
        for unit in army.units:
            await self.micro.retreat(unit)

    async def fight(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.REAPER:
                    await self.micro.reaper(unit)
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight(unit, army.units)
                case UnitTypeId.MARINE:
                    await self.micro.bio_fight(unit, army.units)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_fight(unit, army.units)
                case UnitTypeId.GHOST:
                    await self.micro.ghost(unit, army.units)
                case UnitTypeId.VIKINGFIGHTER:
                    await self.micro.viking(unit, army.units)
                case UnitTypeId.RAVEN:
                    await self.micro.raven(unit, army.units)
                case _:
                    if (self.bot.enemy_units.amount >= 1):
                        closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                        unit.attack(closest_enemy_unit)
                    else:
                        unit.move(army.center)

    async def fight_defense(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight(unit, army.units)
                case UnitTypeId.REAPER:
                    await self.micro.reaper(unit)
                case UnitTypeId.MARINE:
                    await self.micro.bio_defense(unit, army.units)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_defense(unit, army.units)
                case UnitTypeId.GHOST:
                    await self.micro.ghost_defense(unit, army.units)
                case UnitTypeId.VIKINGFIGHTER:
                    await self.micro.viking(unit, army.units)
                case UnitTypeId.RAVEN:
                    await self.micro.raven(unit, army.units)
                case _:
                    closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                    unit.attack(closest_enemy_unit)

    async def fight_drop(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_fight_drop(unit, self.drop_target)
                case UnitTypeId.MARINE:
                    await self.micro.bio_fight(unit, army.units)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_fight(unit, army.units)
                case UnitTypeId.GHOST:
                    await self.micro.ghost(unit, army.units)
                case UnitTypeId.VIKINGFIGHTER:
                    await self.micro.viking(unit, army.units)
                case UnitTypeId.RAVEN:
                    await self.micro.raven(unit, army.units)
                case _:
                    if (self.bot.enemy_units.amount >= 1):
                        closest_enemy_unit: Unit = self.bot.enemy_units.closest_to(unit)
                        unit.attack(closest_enemy_unit)
                    else:
                        unit.move(army.center)
    
    async def disengage(self, army: Army):
        for unit in army.units:
            match unit.type_id:
                case UnitTypeId.MEDIVAC:
                    await self.micro.medivac_disengage(unit, army.units)
                case UnitTypeId.MARINE:
                    await self.micro.bio_disengage(unit)
                case UnitTypeId.MARAUDER:
                    await self.micro.bio_disengage(unit)
                case UnitTypeId.GHOST:
                    await self.micro.bio_disengage(unit)
                case _:
                    await self.micro.retreat(unit)

    
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
        enemies: Units = self.bot.enemy_structures([UnitTypeId.PHOTONCANNON, UnitTypeId.PYLON]).sorted(
            lambda unit: (unit.health + unit.shield, unit.distance_to(self.bot.expansions.b2.position))
        )
        
        # if there are canons, destroy them
        for unit in army.units:
            if (enemies(UnitTypeId.PHOTONCANNON).amount >= 1):
                unit.attack(enemies(UnitTypeId.PHOTONCANNON).first)
            else:
                unit.attack(enemies.first)
            


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
                if (unit.health_percentage >= 0.85):
                    self.micro.stim_bio(unit)
                
                if (unit.type_id == UnitTypeId.REAPER):
                    # if we should use grenade, do it and skip the rest of the logic
                    if (await self.micro.reaper_grenade(unit)):
                        continue
                
                if (unit.type_id == UnitTypeId.RAVEN):
                    await self.micro.raven(unit, army.units)
                    continue
                
                # calculate the range of the unit based on its movement speed + range + cooldown
                range: float = unit.radius + unit.ground_range + unit.real_speed * 1.4 * unit.weapon_cooldown
                closest_worker: Unit = enemy_workers_close.closest_to(unit)
                worker_potential_targets: Units = enemy_workers_close.filter(
                    lambda worker: unit.distance_to(worker) <= range + worker.radius
                ).sorted(
                    lambda worker: ((worker.health + worker.shield), worker.distance_to(unit))
                )

                buildings_in_range: Units = self.bot.enemy_structures.filter(
                    lambda building: unit.target_in_range(building)
                ).sorted(
                    lambda building: (building.type_id not in building_priorities, building.health + building.shield)
                )
                # in these case we should target a worker
                if (worker_potential_targets.amount >= 1 or unit.weapon_cooldown > 0 or buildings_in_range.amount == 0):
                    # define the best target
                    target: Unit = worker_potential_targets.first if worker_potential_targets.amount >= 1 else closest_worker
                    # if we're not on cooldown and workers are really close, run away
                    if (unit.weapon_cooldown > 0):
                        if (enemy_workers_close.closest_distance_to(unit) <= 1.5 and unit.health_percentage < 1):
                            Micro.move_away(unit, enemy_workers_close.closest_to(unit).position, 1)
                        else:
                            # move towards the unit but not too close
                            unit.move(target.position.towards(unit, 3))
                    # if we're on cooldown, shoot at it
                    else:
                        unit.attack(target)
                else:
                    unit.attack(buildings_in_range.first)                    
    
    async def kill_buildings(self, army: Army, radius: float):
        local_enemy_buildings: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.distance_to(army.units.center) <= radius and unit.can_be_attacked
        ).sorted(
            lambda building: (building.type_id not in building_priorities, building.health + building.shield)
        )
        for unit in army.units:
            if (unit.type_id == UnitTypeId.RAVEN):
                self.micro.raven(unit, army)
                continue
            if (unit.type_id == UnitTypeId.MEDIVAC):
                if (unit.cargo_used >= 4):
                    await self.micro.medivac_fight_drop(unit, local_enemy_buildings.first.position)
                else:
                    await self.micro.medivac_fight(unit, army.units)
                continue
            
            if (unit.health_percentage >= 0.85):
                self.micro.stim_bio(unit)
            target: Unit = local_enemy_buildings.first
            if (unit.weapon_cooldown == 0):
                in_range_enemy_buildings: Units = local_enemy_buildings.filter(lambda building: unit.target_in_range(building))
                if (in_range_enemy_buildings.amount >= 1):
                    target = in_range_enemy_buildings.first
            unit.attack(target)

    async def attack_nearest_base(self, army: Army):
        # if army is purely air
        if (not army.leader):
            return
        nearest_base_target: Point2 = self.micro.get_nearest_base_target(army.leader)
        self.micro.attack_a_position(army.leader, nearest_base_target)
        for unit in army.followers:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
                continue
            if (unit.position.distance_to(army.leader.position) >= 3):
                unit.move(army.leader.position)
            else:
                unit.move(center([unit.position, army.leader.position, nearest_base_target]))
        
    async def chase_buildings(self, army: Army):
        # if army is purely air
        if (not army.leader):
            return
        attack_position: Point2 = self.bot.enemy_structures.closest_to(army.leader).position
        self.micro.attack_a_position(army.leader, attack_position)
        for unit in army.followers:
            if (unit.type_id == UnitTypeId.MEDIVAC):
                await self.micro.medivac_fight(unit, army.units)
                continue
            enemy_units_in_range = self.micro.get_enemy_units_in_range(unit)
            if (unit.weapon_cooldown == 0 and enemy_units_in_range.amount >= 1):
                unit.attack(enemy_units_in_range.sorted(lambda unit: (unit.health + unit.shield)).first)
            elif (unit.distance_to(army.leader) >= 3):
                unit.move(army.leader.position)
            else:
                unit.move(center([unit.position, army.leader.position, attack_position]))

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

    def scout(self, army: Army):
        for reaper in army.units:
            if (self.bot.expansions.enemy_b2.is_unknown):
                reaper.move(self.bot.expansions.enemy_b2.mineral_line)
            elif (self.bot.expansions.enemy_main.is_unknown or self.bot.expansions.enemy_main.is_enemy):
                reaper.move(self.bot.expansions.enemy_main.mineral_line)
            else:
                reaper.move(self.bot.expansions.oldest_scout.mineral_line)