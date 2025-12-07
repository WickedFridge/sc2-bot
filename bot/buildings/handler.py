import math
from typing import List, Set
from bot.macro.expansion_manager import Expansions
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.ability_tags import AbilityRepair
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.point2_functions.utils import center, points_to_build_addon
from sc2.game_state import EffectData
from sc2.ids.ability_id import AbilityId
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import must_repair, add_ons, worker_types, menacing, creep

class BuildingsHandler:
    bot: Superbot
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
    
    async def finish_construction(self):
        if (self.bot.workers.collecting.amount == 0):
            return
        
        incomplete_buildings: Units = self.bot.structures.filter(
            lambda structure: (
                structure.build_progress < 1
                and structure.type_id not in add_ons
                and structure.type_id != UnitTypeId.ORBITALCOMMAND
                and structure.type_id != UnitTypeId.PLANETARYFORTRESS
                and self.is_being_constructed(structure) == False
                and self.bot.workers.filter(
                    lambda worker: (
                        worker.is_constructing_scv
                        and worker.orders[0].target == structure.tag
                    )
                ).amount == 0
            )
        )


        for incomplete_building in incomplete_buildings:
            closest_worker: Unit = self.bot.workers.collecting.closest_to(incomplete_building)
            print("ordering SCV to finish", incomplete_building.name)
            closest_worker.smart(incomplete_building)
            
    async def repair_buildings(self):
        if (self.bot.minerals == 0):
            return
        workers = self.bot.workers + self.bot.units(UnitTypeId.MULE)
        available_workers: Units = workers.filter(
            lambda worker: (
                worker.is_moving
                or worker.is_collecting
                or worker.is_idle
                or worker.is_attacking
            )
        )
        workers_repairing: Units = workers.filter(
            lambda worker: (
                len(worker.orders) >= 1
                and worker.orders[0].ability.id in AbilityRepair
            )
        )
        max_workers_repairing: int = min(round(self.bot.supply_workers / 2), self.bot.supply_workers - 6)

        # we don't want under 6 workers mining
        # we don't want over 1/2 of our workers repairing
        if (available_workers.amount <= 6 or workers_repairing.amount >= self.bot.supply_workers / 2):
            print(f'max amount of repairnig workers reached [{workers_repairing.amount}/{max_workers_repairing}]')
            return
        
        burning_buildings_in_pathing = self.bot.structures.ready.filter(
            lambda unit: (
                (
                    unit.is_flying == False or
                    self.bot.in_pathing_grid(unit)
                ) and (
                    unit.health_percentage < 0.6 or
                    (unit.type_id in must_repair and unit.health_percentage < 1)
                )
            )
        )
        for burning_building in burning_buildings_in_pathing:
            workers_repairing_building: Units = workers_repairing.filter(
                lambda unit: unit.order_target == burning_building.tag
            )
            repair_ratio: float = min(1, self.bot.supply_workers / 10)
            max_workers_repairing_building: int = (8 if burning_building.type_id in must_repair else 3) * repair_ratio
            local_avaiable_workers: Units = (
                available_workers.closer_than(6, burning_building)
                if (burning_building.type_id not in must_repair)
                else available_workers.closer_than(12, burning_building)
            )
            if (
                workers_repairing_building.amount >= max_workers_repairing_building
                or workers_repairing.amount >= max_workers_repairing
                or local_avaiable_workers.amount == 0
            ):
                return
            print(f'pulling worker to repair {burning_building.name} [{workers_repairing_building.amount}/{max_workers_repairing}]')
            repairer: Unit = available_workers.closest_to(burning_building)
            repairer.repair(burning_building)
            available_workers.remove(repairer)
            workers_repairing.append(repairer)
            workers_repairing_building.append(repairer)
    
    async def cancel_buildings(self):
        incomplete_buildings: Units = self.bot.structures.filter(
            lambda structure: (
                structure.health_percentage < structure.build_progress < 1
                and structure.type_id not in add_ons
                # and (
                #     self.bot.workers.amount == 0
                #     or self.bot.workers.closest_to(structure).is_constructing_scv == False
                #     or self.bot.workers.closest_distance_to(structure) >= structure.radius * math.sqrt(2)
                # )
                and (
                    (structure.health < 100 and structure.health_percentage < 0.1)
                    or (
                        structure.health_percentage < 0.3
                        and self.bot.scouting.situation == Situation.UNDER_ATTACK
                    )
                )
            )
        )
        for building in incomplete_buildings:
            building(AbilityId.CANCEL_BUILDINPROGRESS)
    
    async def morph_orbitals(self):
        if (self.bot.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9):
            for cc in self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
                if(self.bot.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)):
                    print("Morph Orbital Command")
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def drop_mules(self):
        # find biggest mineral fields near a full base
        safe_mineral_fields: Units = self.bot.expansions.ready.safe.mineral_fields
        if (safe_mineral_fields.amount == 0):
            return
        richest_mineral_field: Unit = max(safe_mineral_fields, key=lambda x: x.mineral_contents)

        # bank scans if we have 3 or more orbitals and enough SCVs
        orbital_command_amount: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        scan_to_bank: int = int(orbital_command_amount / 3) if self.bot.matchup == Matchup.TvZ and self.bot.supply_workers >= 42 else 0
        scan_banked: int = 0
        
        # call down a mule on this guy
        for orbital_command in self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            if (
                orbital_command.energy >= 100
                or scan_banked >= scan_to_bank
            ):
                orbital_command(AbilityId.CALLDOWNMULE_CALLDOWNMULE, richest_mineral_field)
            else:
                scan_banked += 1

    async def scan(self):
        CREEP_DENSITY_THRESHOLD: float = 0.5
        BASE_RADIUS: int = 6
        SCAN_RADIUS: int = 15
        
        orbitals_with_energy: Units = self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).ready.filter(lambda x: x.energy >= 50)
        if (self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount == 0 or orbitals_with_energy.amount == 0):
            return
        
        # if we have no fighting units we can't clean creep
        ravens: Units = self.bot.units(UnitTypeId.RAVEN)
        enemy_units: Units = self.bot.enemy_units
        creep_cleaners: Units = self.bot.units.filter(
            lambda unit: (
                unit.type_id not in worker_types
                and unit.can_attack_ground
                and (
                    ravens.amount == 0
                    or ravens.closer_than(15, unit).amount == 0
                )
                and (
                    enemy_units.amount == 0
                    or enemy_units.closer_than(10, unit).amount == 0
                )
            )
        )

        if (creep_cleaners.amount == 0):
            return
        
        # find bases that have creep around and units who should clean creep
        # Check all owned bases
        creep_layer = self.bot.map.influence_maps.creep
        expansions_to_check: Expansions = self.bot.expansions.taken.copy()
        expansions_to_check.add(self.bot.expansions.next)
        
        for expansion in expansions_to_check:
            density, position = creep_layer.max_density_in_radius(expansion.position, BASE_RADIUS * 2)
            if (position is None):
                continue
            tumors: Units = self.bot.enemy_structures(creep).closer_than(BASE_RADIUS * 2, expansion.position)
            detected: bool = bool(self.bot.map.influence_maps.detection.detected[position])
            if (density > CREEP_DENSITY_THRESHOLD and tumors.amount == 0 and not detected):
                fighting_units_around: Units = creep_cleaners.closer_than(BASE_RADIUS, expansion.position)
                if (fighting_units_around.amount >= 1):
                    print("scanning creep around base")
                    orbital: Unit = orbitals_with_energy.random
                    orbital(AbilityId.SCANNERSWEEP_SCAN, position)
                    # only 1 scan per frame
                    return

        # find fighting units that are on creep without a building in 15 range and not close to an expansion slot (that could have died the last frame)
        enemy_buildings: Units = self.bot.enemy_structures
        on_creep_fighting_units: Units = creep_cleaners.filter(
            lambda unit: (
                self.bot.has_creep(unit.position)
                and self.bot.map.influence_maps.detection.detected[unit.position] == 0
                and (
                    enemy_buildings.amount == 0
                    or enemy_buildings.closest_distance_to(unit) > SCAN_RADIUS
                )
            )
        )

        # scan for creep tumors    
        # look for optimal spot to scan
        best_density: float = 0
        best_position: Point2 = None

        for unit in on_creep_fighting_units:
            # get highest creep density around
            range: float = unit.ground_range
            density, position = creep_layer.max_density_in_radius(unit.position, range)
            if (density > best_density):
                best_density = density
                best_position = position
        
        if (best_density >= CREEP_DENSITY_THRESHOLD):
            orbitals_with_energy.random(AbilityId.SCANNERSWEEP_SCAN, best_position)
            # scan only once per frame
            return

        
        # find invisible enemy unit that we should kill
        enemy_units_to_scan: Units = self.bot.enemy_units.filter(
            lambda unit: (
                not unit.is_visible
                and (unit.is_cloaked or unit.is_burrowed)
                and creep_cleaners.closest_distance_to(unit) < 10
            )
        )
        
        # invisible enemy units we should scan are in range of our fighting units
        for enemy_unit in enemy_units_to_scan:
            print("scan enemy unit", enemy_unit.name)
            orbitals_with_energy.random(AbilityId.SCANNERSWEEP_SCAN, enemy_unit.position)
   
    async def handle_supplies(self):
        supplies_raised: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready
        supplies_lowered: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOTLOWERED)
        minimal_distance: float = 6
        ground_enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.is_flying == False)
        for supply in supplies_raised:
            if (ground_enemy_units.amount == 0 or ground_enemy_units.closest_distance_to(supply) > minimal_distance):
                print("Lower Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        for supply in supplies_lowered:
            if (ground_enemy_units.amount >= 1 and ground_enemy_units.closest_distance_to(supply) <= minimal_distance):
                print("Raise Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_RAISE)

    async def lift_townhalls(self):
        townhalls_not_on_slot = self.bot.expansions.townhalls_not_on_slot.ready.idle
        # calculate the optimal worker count based on mineral field left in bases
        optimal_worker_count: int = (
            sum(expansion.optimal_mineral_workers for expansion in self.bot.expansions.taken)
            + sum(expansion.optimal_vespene_workers for expansion in self.bot.expansions.taken)
        )
        is_mining_optimal: bool = self.bot.supply_workers < optimal_worker_count - 5

        for townhall in townhalls_not_on_slot:
            # don't lift Orbitals after the third CC
            if (townhall.type_id == UnitTypeId.ORBITALCOMMAND):
                if (self.bot.townhalls.ready.amount >= 4):
                    continue
            
            # don't lift CCs before the 4th CC
            if (townhall.type_id == UnitTypeId.COMMANDCENTER):
                if (self.bot.townhalls.ready.amount < 4):
                    continue
            
            # check if we should lift the command center or upgrade it to orbital command
            if (is_mining_optimal and self.bot.townhalls.ready.amount != 4):
                # don't lift this command center because mining is already optimal
                # unless it's to plant the 4th PF
                continue
            landing_spot: Point2 = self.bot.expansions.next.position
            enemy_units_around_spot: Units = self.bot.enemy_units.filter(lambda unit: unit.distance_to(landing_spot) < 10)
            
            if (enemy_units_around_spot.amount >= 1):
                print("too many enemies")
                return

            if (townhall.type_id == UnitTypeId.COMMANDCENTER):
                print("Lift Command Center")
                townhall(AbilityId.LIFT_COMMANDCENTER)
            else:
                print("Lift Orbital")
                townhall(AbilityId.LIFT_ORBITALCOMMAND)

    
    async def land_townhalls(self):
        flying_townhall: Units = self.bot.structures([UnitTypeId.ORBITALCOMMANDFLYING, UnitTypeId.COMMANDCENTERFLYING]).ready.idle
        for townhall in flying_townhall:
            landing_spot: Point2 = (
                self.bot.expansions.next.position if flying_townhall.amount == 1
                else self.bot.expansions.free.closest_to(townhall.position).position if self.bot.expansions.free.amount >= 1
                else self.bot.expansions.last_taken.position
            )
            enemy_units_around_spot: Units = self.bot.enemy_units.filter(lambda unit: unit.distance_to(landing_spot) < 10)
            if (enemy_units_around_spot.amount == 0):
                if (townhall.type_id == UnitTypeId.COMMANDCENTERFLYING):
                    townhall(AbilityId.LAND_COMMANDCENTER, landing_spot)
                else:
                    townhall(AbilityId.LAND_ORBITALCOMMAND, landing_spot)

    async def reposition_buildings(self):
        production_building_ids: List[UnitTypeId] = [
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        ]
        production_buildings_without_addon: Units = self.bot.structures.ready.idle.filter(
            lambda structure: (
                structure.type_id in production_building_ids
                and structure.has_add_on == False
            )
        )
        
        # never reposition the first barrack
        barracks_amount: int = self.bot.structures([UnitTypeId.BARRACKS, UnitTypeId.BARRACKSFLYING]).amount + self.bot.already_pending(UnitTypeId.BARRACKS)
        if (barracks_amount >= 2):
            for production_building in production_buildings_without_addon:
                if not (await self.bot.can_place_single(UnitTypeId.SUPPLYDEPOT, production_building.add_on_position)):
                    print(f'Can not build add-on, {production_building.name} lifts')
                    production_building(AbilityId.LIFT)
        
        # if starport is complete and has no reactor, lift it
        if (
            self.bot.structures(UnitTypeId.STARPORT).ready.amount == 1
            and self.bot.structures(UnitTypeId.STARPORTREACTOR).ready.amount == 0
        ):
            starport = self.bot.structures(UnitTypeId.STARPORT).ready.first
            if (not starport.has_add_on):
                print("Lift Starport")
                starport(AbilityId.LIFT_STARPORT)
        
        # or 2nd starport can't build addon
        if (
            self.bot.structures(UnitTypeId.STARPORT).ready.amount == 2
            and self.bot.structures(UnitTypeId.STARPORTTECHLAB).amount == 0
        ):
            for starport in self.bot.structures(UnitTypeId.STARPORT).ready:
                if (not starport.has_add_on and not self.bot.in_placement_grid(starport.add_on_position)):
                    print("Lift Starport")
                    starport(AbilityId.LIFT_STARPORT)
        
        # if factory is complete with a reactor, lift it
        if (
            (
                self.bot.structures(UnitTypeId.FACTORY).ready.amount >= 1
                and self.bot.structures(UnitTypeId.FACTORYREACTOR).ready.amount >= 1
            )
            or self.bot.structures(UnitTypeId.STARPORTFLYING).ready.amount >= 1
        ):
            for factory in self.bot.structures(UnitTypeId.FACTORY).ready:
                reactors: Units = self.bot.structures(UnitTypeId.REACTOR)
                free_reactors: Units = reactors.filter(
                    lambda reactor: self.bot.in_placement_grid(reactor.add_on_land_position)
                )
                if (factory.has_add_on or free_reactors.amount >= 1):
                    print ("Lift Factory")
                    factory(AbilityId.LIFT_FACTORY)
        
        flying_building_ids: List[UnitTypeId] = [
            UnitTypeId.BARRACKSFLYING,
            UnitTypeId.FACTORYFLYING,
            UnitTypeId.STARPORTFLYING,
        ]
        flying_buildings: Units = self.bot.structures.idle.filter(
            lambda building: building.type_id in flying_building_ids
        )
        
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready + self.bot.structures(UnitTypeId.STARPORTFLYING)
        starports_pending_amount: int = self.bot.already_pending(UnitTypeId.STARPORT)
        starports_without_reactor: Units = starports.filter(lambda starport : starport.has_add_on == False)
        free_reactors: Units = self.bot.structures(UnitTypeId.REACTOR).filter(
            lambda reactor: self.bot.in_placement_grid(reactor.add_on_land_position)
        )
                    
        for flying_building in flying_buildings:
            match (flying_building.type_id):
                case UnitTypeId.BARRACKSFLYING:
                    land_position: Point2 = dfs_in_pathing(self.bot, flying_building.position, self.bot.game_info.map_center, 1, True)
                    flying_building(AbilityId.LAND, land_position)    
                case UnitTypeId.FACTORYFLYING:
                    land_position: Point2 = dfs_in_pathing(self.bot, flying_building.position, self.bot.game_info.map_center, 1, True)
                    flying_building(AbilityId.LAND, land_position)
                    # if (
                    #     free_reactors.amount <= 1 and
                    #     (starports_pending_amount >= 1 or starports_without_reactor.amount >= 1)
                    # ):
                    #     land_position: Point2 = dfs_in_pathing(self.bot, flying_building.position, self.bot.game_info.map_center, 1, True)
                    #     flying_building(AbilityId.LAND, land_position)
                case UnitTypeId.STARPORTFLYING:
                    if (free_reactors.amount >= 1):
                        print("Land Starport")
                        closest_free_reactor = free_reactors.closest_to(flying_building)
                        flying_building(AbilityId.LAND, closest_free_reactor.add_on_land_position)
                    else:
                        building_factory_reactors: Units = self.bot.structures(UnitTypeId.FACTORYREACTOR).filter(
                            lambda reactor: reactor.build_progress < 1
                        )
                        if (building_factory_reactors.amount >= 1):                
                            # print("Move Starport over Factory building Reactor")
                            flying_building.move(building_factory_reactors.closest_to(flying_building).add_on_land_position)
                        elif (starports.amount >= 2):
                            land_position: Point2 = dfs_in_pathing(self.bot, flying_building.position, self.bot.game_info.map_center, 1, True)
                            flying_building(AbilityId.LAND, land_position)
                        else:
                            print("no free reactor")

    async def salvage_bunkers(self) -> None:
        planetaries: Units = self.bot.structures(UnitTypeId.PLANETARYFORTRESS)
        if (planetaries.amount == 0):
            return
        
        BASE_SIZE: int = 12
        bunkers_to_salvage: Units = self.bot.structures(UnitTypeId.BUNKER).filter(
            lambda unit: (
                unit.cargo_used == 0
                and planetaries.closest_distance_to(unit) <= BASE_SIZE
            )
        )
        for bunker in bunkers_to_salvage:
            bunker(AbilityId.SALVAGEEFFECT_SALVAGE)
    
    async def find_land_position(self, building: Unit):
        possible_land_positions_offset = sorted(
            (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
            key=lambda point: point.x**2 + point.y**2,
        )
        offset_point: Point2 = Point2((-0.5, -0.5))
        possible_land_positions = (building.position.rounded + offset_point + p for p in possible_land_positions_offset)
        for target_land_position in possible_land_positions:
            land_and_addon_points: List[Point2] = self.building_land_positions(target_land_position)
            if all(await self.bot.can_place(UnitTypeId.SUPPLYDEPOT, land_and_addon_points)):
                print(building.name, " found a position to land")
                building(AbilityId.LAND, target_land_position)
                break

    def building_land_positions(self, sp_position: Point2) -> List[Point2]:
        """ Return all points that need to be checked when trying to land at a location where there is enough space to build an addon. Returns 13 points. """
        land_positions = [(sp_position + Point2((x, y))).rounded for x in range(-1, 2) for y in range(-1, 2)]
        return land_positions + points_to_build_addon(sp_position)
 
    
    def scv_build_progress(self, scv: Unit) -> float:
        if (not scv.is_constructing_scv):
            return 1
        building: Unit = self.bot.structures.closest_to(scv)
        return 1 if building.is_ready else building.build_progress
    
    def is_being_constructed(self, building: Unit) -> bool:
        return (
            self.bot.workers.closest_to(building).is_constructing_scv == True
            or self.bot.workers.closest_distance_to(building) <= building.radius * math.sqrt(2)
        )