import math
from typing import List, Set
from bot.macro.expansion_manager import Expansions
from bot.utils.ability_tags import AbilityRepair
from bot.utils.point2_functions import center
from bot.utils.unit_functions import worker_amount_vespene_geyser, worker_amount_mineral_field
from sc2.bot_ai import BotAI
from sc2.game_state import EffectData
from sc2.ids.ability_id import AbilityId
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import must_repair, add_ons, worker_types

class BuildingsHandler:
    bot: BotAI
    expansions: Expansions
    
    def __init__(self, bot, expansions) -> None:
        super().__init__()
        self.bot = bot
        self.expansions = expansions

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
            )
        )
        for incomplete_building in incomplete_buildings:
            closest_worker: Unit = self.bot.workers.collecting.closest_to(incomplete_building)
            print("ordering SCV to finish", incomplete_building.name)
            closest_worker.smart(incomplete_building)
            
    async def repair_buildings(self):
        workers = self.bot.workers + self.bot.units(UnitTypeId.MULE)
        available_workers: Units = workers.filter(
            lambda worker: worker.is_moving or worker.is_collecting or worker.is_idle
        )
        if (self.bot.minerals < 50):
            return
        if (available_workers.amount == 0):
            print("no workers to repair o7")
            return
        burning_buildings = self.bot.structures.ready.filter(
            lambda unit: unit.health_percentage < 0.6 or (unit.type_id == UnitTypeId.BUNKER and unit.health_percentage < 1)
        )
        for burning_building in burning_buildings:
            repairing_workers: Units = workers.filter(
                lambda unit: (
                    unit.orders.__len__()
                    and unit.orders[0].ability.id in AbilityRepair
                    and unit.order_target == burning_building.tag
                )
            )
            if (
                (burning_building.type_id in must_repair and repairing_workers.amount < 8)
                or repairing_workers.amount < 3
            ):
                print("pulling worker to repair", burning_building.name)
                
                available_workers.closest_to(burning_building).repair(burning_building)
    
    async def cancel_buildings(self):
        incomplete_buildings: Units = self.bot.structures.filter(
            lambda structure: (
                structure.build_progress < 1
                and structure.type_id not in add_ons
                and (
                    self.bot.workers.amount == 0
                    or self.bot.workers.closest_to(structure).is_constructing_scv == False
                    or self.bot.workers.closest_distance_to(structure) >= structure.radius * math.sqrt(2)
                )
                and structure.health < 50
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
        mineral_fields: Units = Units([], self.bot)
        ready_townhalls: Units = self.bot.structures(UnitTypeId.COMMANDCENTER).ready + self.bot.structures(UnitTypeId.ORBITALCOMMAND) 
        for townhall in ready_townhalls :
            mineral_fields += self.bot.mineral_field.closer_than(10, townhall)

        if (mineral_fields.amount == 0):
            return
        enemy_units: Units = self.bot.enemy_units
        safe_mineral_fields: Units = (
            mineral_fields if enemy_units.amount == 0 else
            mineral_fields.filter(lambda unit: self.bot.enemy_units.closest_distance_to(unit) > 15)
        )
        if (safe_mineral_fields.amount == 0):
            return
        richest_mineral_field: Unit = max(safe_mineral_fields, key=lambda x: x.mineral_contents)

        # call down a mule on this guy
        # also bank a scan if we have 3 or more orbitals
        orbital_command_amount: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        # scan_to_bank: int = int(orbital_command_amount / 3)
        scan_to_bank: int = 3
        scan_banked: int = 0
        for orbital_command in self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            if (
                orbital_command.energy >= 100
                or scan_banked >= scan_to_bank
            ):
                orbital_command(AbilityId.CALLDOWNMULE_CALLDOWNMULE, richest_mineral_field)
            else:
                scan_banked += 1

    async def scan(self):
        if (self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount == 0):
            return
        
        # find invisible enemy unit that we should kill
        invisible_enemy_units: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
            lambda unit: unit.is_visible and not unit.is_revealed and (unit.is_cloaked or unit.is_burrowed) 
        )
        
        # if we have a unit close to it that can attack it
        fighting_units: Units = self.bot.units.filter(
            lambda unit: (unit.type_id not in worker_types)
        )

        # find fighting units that are on creep without a building in 5 range
        on_creep_fighting_units: Units = fighting_units.filter(
            lambda unit: (
                self.bot.has_creep(unit.position)
                and not self.bot.enemy_structures.closer_than(10, unit.position).amount
            )
        )

        # scan units that are on creep
        for unit in on_creep_fighting_units:
            # get ongoing scans
            scans: Set[EffectData] = set(filter(lambda effect: effect.id == EffectId.SCANNERSWEEP, self.bot.state.effects))
            # if there is no scan on this unit, scan it
            scanned: bool = False
            for scan in scans:
                scan_center: Point2 = center(list(scan.positions))
                if (scan_center.distance_to(unit.position) < 10):
                    scanned = True
                    break
            if (not scanned):
                print("scan unit on creep", unit.name)
                # find an orbital command with enough energy
                orbitals_with_energy: Units = self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).ready.filter(lambda x: x.energy >= 50)
                if (orbitals_with_energy.amount == 0):
                    print("No orbital command with enough energy to scan")
                    return
                orbitals_with_energy.random(AbilityId.SCANNERSWEEP_SCAN, unit.position)
                # scan only once per frame
                return
            else:        
                print("Unit is already scanned", unit.name)

        
        # # invisible enemy units we should scan are in range of our fighting units
        # for enemy_unit in invisible_enemy_units.in_distance_of_group(fighting_units, 10):
        #     print("Should scan enemy unit", enemy_unit.name)
        #     # find an orbital command with enough energy
        #     orbitals_with_energy: Units = self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).ready.filter(lambda x: x.energy >= 50)
        #     if (orbitals_with_energy.amount == 0):
        #         print("No orbital command with enough energy to scan")
        #         return
        #     print("scan enemy unit", enemy_unit.name)
        #     orbitals_with_energy.random(AbilityId.SCANNERSWEEP_SCAN, enemy_unit.position)

    
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

    async def lift_orbital(self):
        if (self.expansions.free.amount == 0):
            return
        orbitals_not_on_slot = self.expansions.townhalls_not_on_slot(UnitTypeId.ORBITALCOMMAND).idle
        for orbital in orbitals_not_on_slot:
            landing_spot: Point2 = self.expansions.next.position
            enemy_units_around_spot: Units = self.bot.enemy_units.filter(lambda unit: unit.distance_to(landing_spot) < 10)
            
            # calculate the optimal worker count based on mineral field left in bases
            optimal_worker_count: int = (
                sum(expansion.optimal_mineral_workers for expansion in self.expansions.taken)
                + sum(expansion.optimal_vespene_workers for expansion in self.expansions.taken)
            )
            if (enemy_units_around_spot.amount >= 1):
                print("too many enemies")
                return
            if (
                self.bot.supply_workers >= optimal_worker_count - 5
                or self.expansions.townhalls_not_on_slot().amount >= 2
            ):
                print("Lift Orbital")
                orbital(AbilityId.LIFT_ORBITALCOMMAND)

    async def land_orbital(self):
        flying_orbitals: Units = self.bot.structures(UnitTypeId.ORBITALCOMMANDFLYING).ready.idle
        for orbital in flying_orbitals:
            landing_spot: Point2 = (
                self.expansions.next.position if flying_orbitals.amount == 1
                else self.expansions.free.closest_to(orbital.position).position if self.expansions.free.amount >= 1
                else self.expansions.last_taken.position
            )
            enemy_units_around_spot: Units = self.bot.enemy_units.filter(lambda unit: unit.distance_to(landing_spot) < 10)
            if (enemy_units_around_spot.amount == 0):
                orbital(AbilityId.LAND_ORBITALCOMMAND, landing_spot)

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
        for production_building in production_buildings_without_addon:
            if not (await self.bot.can_place_single(UnitTypeId.SUPPLYDEPOT, production_building.add_on_position)):
                print(f'Can not build add-on, {production_building.name} lifts')
                production_building(AbilityId.LIFT)
        
        # if starport is complete and has no reactor, lift it
        if (
            self.bot.structures(UnitTypeId.STARPORT).ready.amount >= 1
            and self.bot.structures(UnitTypeId.STARPORTREACTOR).ready.amount < self.bot.structures(UnitTypeId.STARPORT).ready.amount
        ):
            for starport in self.bot.structures(UnitTypeId.STARPORT).ready:
                if (not starport.has_add_on):
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
        for flying_building in flying_buildings:
            match (flying_building.type_id):
                case UnitTypeId.BARRACKSFLYING:
                    await self.find_land_position(flying_building)
                case UnitTypeId.FACTORYFLYING:
                    starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready + self.bot.structures(UnitTypeId.STARPORTFLYING)
                    starports_pending_amount: int = self.bot.already_pending(UnitTypeId.STARPORT)
                    starports_without_reactor: Units = starports.filter(lambda starport : starport.has_add_on == False)
                    free_reactors: Units = self.bot.structures(UnitTypeId.REACTOR).filter(
                        lambda reactor: self.bot.in_placement_grid(reactor.add_on_land_position)
                    )
                    if (
                        free_reactors.amount <= 1 and
                        (starports_pending_amount >= 1 or starports_without_reactor.amount >= 1)
                    ):
                        await self.find_land_position(flying_building)
                case UnitTypeId.STARPORTFLYING:
                    reactors: Units = self.bot.structures(UnitTypeId.REACTOR)
                
                    free_reactors: Units = reactors.filter(
                        lambda reactor: self.bot.in_placement_grid(reactor.add_on_land_position)
                    )
                    if (free_reactors.amount >= 1):
                        print("Land Starport")
                        closest_free_reactor = free_reactors.closest_to(flying_building)
                        flying_building(AbilityId.LAND, closest_free_reactor.add_on_land_position)
                    else:
                        building_factory_reactors: Units = self.bot.structures(UnitTypeId.FACTORYREACTOR).filter(
                            lambda reactor: reactor.build_progress < 1
                        )
                        if (building_factory_reactors):                
                            # print("Move Starport over Factory building Reactor")
                            flying_building.move(building_factory_reactors.closest_to(flying_building).add_on_land_position)
                        else:
                            print("no free reactor")

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
        return land_positions + self.points_to_build_addon(sp_position)
    
    
    def points_to_build_addon(self, building_position: Point2) -> List[Point2]:
        """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
        addon_offset: Point2 = Point2((2.5, -0.5))
        addon_position: Point2 = building_position + addon_offset
        addon_points = [
            (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
        ]
        return addon_points
    
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