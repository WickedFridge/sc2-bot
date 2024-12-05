import math
from typing import List
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from .utils.unit_tags import tower_types, worker_types, dont_attack, hq_types

class Combat:
    bot: BotAI
    workers_pulled_amount: int = 0
    enemy_threats_amount: int = 0
    enemy_towers_amount: int = 0
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    async def pull_workers(self):
        # fill bunkers
        # for bunker in self.structures(UnitTypeId.BUNKER).ready:
        #     for marine in self.units(UnitTypeId.MARINE).closest_n_units(bunker, 4):
        #         marine(AbilityId.LOAD_BUNKER, bunker)
        if not self.bot.panic_mode:
            # ask all chasing SCVs to stop
            attacking_workers = self.bot.workers.filter(
                lambda unit: unit.is_attacking
            )
            for attacking_worker in attacking_workers:
                attacking_worker.stop()
            return

        if self.bot.workers.collecting.amount == 0:
            print("no workers to pull, o7")
            return

        # if every townhalls is dead, just attack the nearest unit with every worker
        if (self.bot.townhalls.amount == 0):
            print("no townhalls left, o7")
            for worker in self.bot.workers:
                worker.attack(self.bot.enemy_units.closest_to(worker))
            return
        
        for cc in self.bot.townhalls:
            # define threats in function of distance to townhalls
            # threats need to be attackable, ground units close to a CC

            enemy_threats = self.bot.enemy_units.filter(
                lambda unit: unit.distance_to(cc) <= 10 and unit.can_be_attacked and not unit.is_flying
            )
            
            enemy_towers: Units = self.bot.enemy_structures.filter(
                lambda unit: unit.type_id in tower_types and unit.distance_to(cc) <= 20
            )

            if (enemy_threats.amount != self.enemy_threats_amount or enemy_towers.amount != self.enemy_towers_amount):
                self.enemy_threats_amount = enemy_threats.amount
                self.enemy_towers_amount = enemy_towers.amount
                print("panic attack : ", enemy_towers.amount, "enemy towers, ", enemy_threats.amount, "enemy units")
            # respond to canon/bunker/spine rush
            for tower in enemy_towers:
                # Pull 3 workers by tower by default, less if we don't have enough
                # Only pull workers if we don't have enough workers attacking yet
                workers_attacking_tower = self.bot.workers.filter(
                    lambda unit: unit.is_attacking and unit.order_target == tower.tag
                ).amount
                if (workers_attacking_tower >= 3):
                    break

                amount_to_pull: int = 3 - workers_attacking_tower
                workers: Units = self.bot.workers.collecting.sorted_by_distance_to(tower)

                workers_pulled: Units = workers[:amount_to_pull] if workers.amount >= amount_to_pull else workers

                for worker_pulled in workers_pulled:
                    worker_pulled.attack(tower)

            # collecting workers close to threats should be pulled
            workers: Units = self.bot.workers.collecting
            
            for threat in enemy_threats:
                closest_worker: Unit = workers.closest_to(threat)
                
                # handle scouting worker identified as threat
                if threat.type_id in worker_types:
                    # if no scv is already chasing
                    attacking_workers: Unit = self.bot.workers.filter(
                        lambda unit: unit.is_attacking and unit.order_target == threat.tag
                    )
                    if (attacking_workers.amount == 0):
                        # pull 1 scv to follow it
                        closest_worker.attack(threat)
                # else pull against close units
                elif (closest_worker.distance_to(threat) <= 20):
                        closest_worker.attack(threat)

            workers_pulled_amount: int = self.bot.workers.filter(lambda unit: unit.is_attacking).amount
            if (workers_pulled_amount != self.workers_pulled_amount):
                self.workers_pulled_amount = workers_pulled_amount
                print(workers_pulled_amount, "workers pulled")


    async def attack(self):
        marines: Units = self.bot.units(UnitTypeId.MARINE).ready
        medivacs: Units = self.bot.units(UnitTypeId.MEDIVAC).ready
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        
        army = (marines + medivacs)

        for medivac in medivacs:
            # if not boosting, boost
            available_abilities = (await self.bot.get_available_abilities([medivac]))[0]
            if AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS in available_abilities:
                medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
            
            # heal closest damaged ally
            damaged_allies: Units = self.bot.units.filter(
                lambda unit: (
                    unit.is_biological
                    and unit.health_percentage < 1
                )
            )

            if (damaged_allies.amount >= 1):
                medivac(AbilityId.MEDIVACHEAL_HEAL,damaged_allies.closest_to(medivac))
            else:
                closest_marines: Units = marines.closest_n_units(enemy_main_position, marines.amount // 2)
                if (closest_marines.amount >= 1):
                    medivac.move(closest_marines.center)
                elif (self.bot.townhalls.amount >= 1):
                    medivac.move(self.bot.townhalls.closest_to(enemy_main_position))


        for marine in marines:            
            enemy_units = self.bot.enemy_units.filter(lambda unit: not unit.is_structure and unit.can_be_attacked and unit.type_id not in dont_attack)
            enemy_towers = self.bot.enemy_structures.filter(lambda unit: unit.type_id in tower_types)
            enemy_units += enemy_towers
            enemy_buildings = self.bot.enemy_structures.filter(lambda unit: unit.can_be_attacked)

            enemy_units_in_range: Units = enemy_units.filter(
                lambda unit: marine.target_in_range(unit)
            )
            enemy_units_in_sight: Units = enemy_units.filter(
                lambda unit: unit.distance_to(marine) <= 20 
            )
            enemy_units_outside_of_range: Units = enemy_units.filter(
                lambda unit: not marine.target_in_range(unit)
            )
            enemy_buildings_in_range: Units = enemy_buildings.filter(
                lambda unit: marine.target_in_range(unit)
            )
            enemy_buildings_outside_of_range: Units = enemy_buildings.filter(
                lambda unit: not marine.target_in_range(unit)
            )

            # If units in sight, should be stimmed
            # For building we only stim if high on life
            if (
                (enemy_units_in_sight or (enemy_buildings_in_range and marine.health >= 45))
                and self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
                and not marine.has_buff(BuffId.STIMPACK)
            ):
                marine(AbilityId.EFFECT_STIM_MARINE)
            
            
            # If units in range, attack the one with the least HPs, closest if tied (don't forget to stim first if not)
            if (enemy_units_in_range) :
                enemy_units_in_range.sort(
                    key=lambda unit: unit.health
                )
                if (marine.weapon_ready):
                    marine.attack(enemy_units_in_range[0])
                else:
                    # only run away from unit with smaller range that are facing (chasing us)
                    closest_enemy: Unit = enemy_units_in_range.closest_to(marine)
                    if(
                        (closest_enemy.can_attack or closest_enemy.type_id == UnitTypeId.BANELING)
                        and closest_enemy.is_facing(marine, math.pi)
                        and closest_enemy.ground_range < marine.ground_range
                    ):
                        self.move_away(marine, closest_enemy)
                    # else:
                    #     marine.move(closest_enemy)
            
            elif (enemy_units_in_sight) :
                marine.attack(enemy_units_in_sight.closest_to(marine))
            elif (enemy_buildings_in_range) :
                marine.attack(enemy_buildings_in_range.closest_to(marine))
            elif (marines.amount > 10) :
                # find nearest opposing townhalls
                
                enemy_workers: Units = self.bot.enemy_units.filter(lambda unit: unit.type_id in worker_types)
                enemy_bases: Units = self.bot.enemy_structures.filter(lambda structure: structure.type_id in hq_types)
                close_army: Units = army.closest_n_units(enemy_main_position, army.amount // 2)

                if (enemy_workers.amount):
                    marine.attack(enemy_workers.closest_to(marine))

                # group first
                elif (marine.distance_to(close_army.center) > 10):
                    marine.move(close_army.center)
                
                # attack nearest base
                elif (enemy_bases.amount):
                    marine.move(enemy_bases.closest_to(marine))
                
                # attack nearest building
                elif (enemy_buildings_outside_of_range.amount >= 1):
                    marine.move(enemy_buildings_outside_of_range.closest_to(marine))
                
                # attack enemy location
                else:
                    marine.attack(enemy_main_position)
            elif (
                enemy_units_outside_of_range.amount >= 1
            ):
                distance_to_hq: float = enemy_units_outside_of_range.closest_distance_to(self.bot.townhalls.first)
                distance_to_oppo: float = enemy_units_outside_of_range.closest_distance_to(enemy_main_position)
                
                # meet revealed enemy outside of range if they are in our half of the map
                if (distance_to_hq < distance_to_oppo):
                    for marine in marines:
                        marine.move(enemy_units_outside_of_range.closest_to(marine))
            else:
                for marine in army:
                    if (self.bot.townhalls.amount == 0):
                        break
                    marine.move(self.bot.townhalls.closest_to(enemy_main_position))

    async def detect_panic(self):
        panic_mode: bool = False
        # if enemies in range of a CC, activate panic mode
        for cc in self.bot.townhalls:
            threats = (
                self.bot.enemy_units + self.bot.enemy_structures
            ).filter(lambda unit: unit.distance_to(cc) <= 12)
            
            if (threats.amount >= 1):
                panic_mode = True
                break
        if self.bot.panic_mode != panic_mode:
            print("Panic mode:", panic_mode)
            self.bot.panic_mode = panic_mode

            
    def away(self, selected: Unit, enemy: Unit, distance: int = 2):
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        return selected_position.towards(target, distance)


    def move_away(self, selected: Unit, enemy: Unit, distance: int = 2):
        # print("Moving away 1 from 2", selected.name, enemy.name)
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        selected.move(selected_position.towards(target, distance))