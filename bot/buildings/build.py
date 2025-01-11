import math
from typing import FrozenSet, List, Literal, Set
from bot.utils.ability_tags import AbilityBuild
from sc2.bot_ai import BotAI
from sc2.game_info import Ramp
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit import Unit, UnitOrder
from sc2.units import Units
from ..utils.unit_tags import add_ons

class Build:
    bot: BotAI
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot


    async def finish_construction(self):
        if (self.bot.workers.collecting.amount == 0):
            print("no workers to finish buildings o7")
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

    async def supplies(self):
        # move SCV for first depot
        workers_mining: int = self.bot.workers.collecting.amount
        if (
            self.bot.supply_used == 13
            and workers_mining == self.bot.supply_used
            and self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready.amount == 0
            and self.bot.minerals >= 60
        ):
            print("move worker for first depot")
            self.bot.workers.random.move(self.bot.main_base_ramp.depot_in_middle)
        
        supply_placement_positions: FrozenSet[Point2] = self.bot.main_base_ramp.corner_depots
        depots: Units = self.bot.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})

        # Filter locations close to finished supply depots
        if depots:
            supply_placement_positions: Set[Point2] = {
                d
                for d in supply_placement_positions if depots.closest_distance_to(d) > 1
            }
            
        if (
            self.bot.supply_cap < 200
            and self.bot.supply_left < 2 + self.bot.supply_used / 10
            and self.bot.can_afford(UnitTypeId.SUPPLYDEPOT)
            and self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) <= self.bot.supply_used / 50
        ) :
            print("Build Supply Depot")
            if (len(supply_placement_positions) >= 1) :
                target_supply_location: Point2 = supply_placement_positions.pop()
                await self.build(UnitTypeId.SUPPLYDEPOT, target_supply_location)
            else:
                workers: Units = self.bot.workers.collecting
                if (workers):
                    worker: Unit = workers.furthest_to(workers.center)
                    await self.build(UnitTypeId.SUPPLYDEPOT, worker.position)


    async def gas(self):
        gasCount: int = self.bot.structures(UnitTypeId.REFINERY).ready.amount + self.bot.already_pending(UnitTypeId.REFINERY)
        workers_mining: int = self.bot.workers.collecting.amount
        if(
            self.bot.can_afford(UnitTypeId.REFINERY)
            and gasCount <= 2 * self.bot.townhalls.ready.amount
            and self.bot.structures(UnitTypeId.BARRACKS).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKS) >= 1
            and workers_mining >= (gasCount + 1) * 11.5
            and (not self.bot.waitingForOrbital() or self.bot.minerals >= 225)
        ):
            for th in self.bot.townhalls.ready:
                # Find all vespene geysers that are closer than range 10 to this townhall
                print("Build Gas")
                vgs: Units = self.bot.vespene_geyser.closer_than(10, th)
                if (vgs.amount >= 1):
                    await self.bot.build(UnitTypeId.REFINERY, vgs.random)
                    break


    async def barracks(self):
        barracks_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.BARRACKS)
        barracksPosition: Point2 = self.bot.main_base_ramp.barracks_correct_placement
        barracks_amount: int = self.bot.structures(UnitTypeId.BARRACKS).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKS) + self.bot.structures(UnitTypeId.BARRACKSFLYING).ready.amount
        cc_amount: int = self.bot.townhalls.amount
        max_barracks: int = min(20, cc_amount ** 2 / 2 - cc_amount / 2 + 1)

        # We want 1 rax for 1 base, 2 raxes for 2 bases, 4 raxes for 3 bases, 7 raxes for 4 bases
        # y = x²/2 - x/2 + 1 where x is the number of bases and y the number of raxes
        # with a max of 20 raxes

        if (
            barracks_tech_requirement == 1
            and self.bot.can_afford(UnitTypeId.BARRACKS)
            and self.bot.already_pending(UnitTypeId.BARRACKS) < self.bot.townhalls.amount
            and barracks_amount < max_barracks
            and not self.bot.waitingForOrbital()
        ) :
            print(f'Build Barracks [{barracks_amount + 1}/{int(max_barracks)}]')
            if (barracks_amount >= 1 and cc_amount >= 1):
                cc: Unit =  self.bot.townhalls.ready.random if self.bot.townhalls.ready.amount >= 1 else self.bot.townhalls.random
                barracksPosition = cc.position.towards(self.bot.game_info.map_center, 4)
            await self.build(UnitTypeId.BARRACKS, barracksPosition)
    

    async def factory(self):
        facto_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.FACTORY)
        max_factories: int = 1
        factories_count: int = (
            self.bot.structures(UnitTypeId.FACTORY).ready.amount
            + self.bot.structures(UnitTypeId.FACTORYFLYING).ready.amount
            + self.bot.already_pending(UnitTypeId.FACTORY)
        )

        # We want 1 factory so far
        if (
            facto_tech_requirement == 1
            and self.bot.townhalls.amount >= 2
            and self.bot.can_afford(UnitTypeId.FACTORY)
            and self.bot.already_pending(UnitTypeId.FACTORY) < 1
            and factories_count < max_factories
            and not self.bot.waitingForOrbital()
        ) :
            print("Build Factory")
            cc: Unit = self.bot.townhalls.ready.random
            factory_position = cc.position.towards(self.bot.game_info.map_center, 4)
            await self.build(UnitTypeId.FACTORY, factory_position)


    async def starport(self):
        starport_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.STARPORT)
        max_starport: int = 1
        starport_count: int = self.bot.structures(UnitTypeId.STARPORT).ready.amount + self.bot.structures(UnitTypeId.STARPORTFLYING).ready.amount + self.bot.already_pending(UnitTypeId.STARPORT)

        # We want 1 starport so far
        if (
            starport_tech_requirement == 1
            and self.bot.townhalls.amount >= 2
            and self.bot.can_afford(UnitTypeId.STARPORT)
            and self.bot.already_pending(UnitTypeId.STARPORT) <= 2
            and not self.bot.structures(UnitTypeId.STARPORT)
            and starport_count < max_starport
            and not self.bot.waitingForOrbital()
        ) :
            print("Build Starport close to Factory")
            factories: Units = self.bot.structures(UnitTypeId.FACTORY).ready
            ccs: Units = self.bot.townhalls
            if (factories):
                starport_position = factories.random.position.towards(self.bot.game_info.map_center, 2)
            else:
                starport_position = ccs.random.position.towards(self.bot.game_info.map_center, 2)
            await self.build(UnitTypeId.STARPORT, starport_position)


    async def bunker(self):
        bunker_tech_requirements: float = self.bot.tech_requirement_progress(UnitTypeId.BUNKER)
        bunker_count: float = self.bot.structures(UnitTypeId.BUNKER).ready.amount + self.bot.already_pending(UnitTypeId.BUNKER)
        orbital_count: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount

        # We want a bunker at each base after the first
        if (bunker_tech_requirements == 1
            and orbital_count >= 1
            and bunker_count < self.bot.townhalls.amount - 1
            and self.bot.can_afford(UnitTypeId.BUNKER)
        ):
            townhalls: Units = self.bot.townhalls.copy()
            bunkers: Units = self.bot.structures(UnitTypeId.BUNKER)
            bases_without_bunkers = townhalls.filter(lambda unit: bunkers.amount == 0 or bunkers.closest_distance_to(unit) > 5)
            bases_without_bunkers.sort(key = lambda unit: unit.distance_to(self.bot.start_location), reverse=True)
            last_base: Unit = bases_without_bunkers.first
            closest_ramp_bottom: Point2 = self.find_closest_bottom_ramp(last_base.position).bottom_center
            second_to_last_base: Unit = bases_without_bunkers.first if (bases_without_bunkers.amount == 1) else bases_without_bunkers[1]
            enemy_spawn: Point2 = self.bot.enemy_start_locations[0]
            bunker_position: Point2 = last_base.position.towards(enemy_spawn, 3)
            if (bunker_position.distance_to(closest_ramp_bottom) < 15):
                bunker_position = bunker_position.towards(closest_ramp_bottom, 3)
            else:
                bunker_position = bunker_position.towards(second_to_last_base, 2)
            print("build bunker near last base")
            await self.build(UnitTypeId.BUNKER, bunker_position)


    async def ebays(self):
        ebay_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.ENGINEERINGBAY)
        ebays_count: int = self.bot.structures(UnitTypeId.ENGINEERINGBAY).ready.amount + self.bot.already_pending(UnitTypeId.ENGINEERINGBAY)
        staport_count: float = (
            self.bot.structures(UnitTypeId.STARPORT).amount
            + self.bot.structures(UnitTypeId.STARPORTFLYING).amount
            + self.bot.already_pending(UnitTypeId.STARPORT)
        )

        # We want 2 ebays once we have a 3rd CC and a Starport
        if (
            ebay_tech_requirement == 1
            and self.bot.can_afford(UnitTypeId.ENGINEERINGBAY)
            and ebays_count < 2
            and self.bot.townhalls.amount >= 3
            and staport_count >= 1
            and not self.bot.waitingForOrbital()
        ) :
            print("Build EBay")
            ebay_position = await self.bot.find_placement(UnitTypeId.ENGINEERINGBAY, near=self.bot.townhalls.ready.center)
            if (ebay_position):
                await self.build(UnitTypeId.ENGINEERINGBAY, ebay_position)


    async def armory(self):
        armory_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.ARMORY)
        upgrades_tech_requirement: float = self.bot.already_pending_upgrade(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
        armory_count: int = self.bot.structures(UnitTypeId.ARMORY).ready.amount + self.bot.already_pending(UnitTypeId.ARMORY)

        # We want 1 armory once we have a +1 60% complete
        if (
            armory_tech_requirement == 1
            and upgrades_tech_requirement >= 0.6
            and self.bot.can_afford(UnitTypeId.ARMORY)
            and armory_count == 0
            and self.bot.townhalls.amount >= 1
        ) :
            print("Build Armory")
            armory_location = self.bot.townhalls.closest_n_units(self.bot.townhalls.ready.first, 2).center
            armory_position = await self.bot.find_placement(UnitTypeId.ARMORY, near=armory_location)
            if (armory_position):
                await self.bot.build(UnitTypeId.ARMORY, armory_position)


    async def addons(self):
        await self.barracks_addons()
        await self.factories_addons()


    async def barracks_addons(self):
        # Loop over each Barrack without an add-on
        for barrack in self.bot.structures(UnitTypeId.BARRACKS).ready.filter(
            lambda barrack: barrack.has_add_on == False
        ):
            if (
                not barrack.is_idle
                or self.bot.units(UnitTypeId.MARINE).ready.amount < 2
            ):
                break
            
            if not (await self.bot.can_place_single(UnitTypeId.SUPPLYDEPOT, barrack.add_on_position)):
                print("Can't build add-on, Barracks lifts")
                barrack(AbilityId.LIFT_BARRACKS)
                
            # If we have the same number of techlabs & reactor, we build a techlab, otherwise we build a reactor
            techlab_amount = self.bot.structures(UnitTypeId.BARRACKSTECHLAB).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKSTECHLAB)
            reactor_amount = self.bot.structures(UnitTypeId.BARRACKSREACTOR).ready.amount + self.bot.already_pending(UnitTypeId.BARRACKSREACTOR)
            if (
                techlab_amount <= reactor_amount):
                if (self.bot.can_afford(UnitTypeId.BARRACKSTECHLAB)):
                    barrack.build(UnitTypeId.BARRACKSTECHLAB)
                    print("Build Techlab")
            else:
                if (self.bot.can_afford(UnitTypeId.BARRACKSREACTOR)):
                    barrack.build(UnitTypeId.BARRACKSREACTOR)
                    print("Build Reactor")

        # Loop over each flying Barrack
        for barrack in self.bot.structures(UnitTypeId.BARRACKSFLYING).idle:
            await self.find_land_position(barrack)


    async def factories_addons(self):
        # Loop over each Factory without an add-on
        for factory in self.bot.structures(UnitTypeId.FACTORY).ready.idle.filter(
            lambda factory: factory.has_add_on == False
        ):
            if (
                not self.bot.can_afford(UnitTypeId.FACTORYREACTOR)
                or (
                    self.bot.structures(UnitTypeId.STARPORT).ready.amount
                    + self.bot.structures(UnitTypeId.STARPORTFLYING).ready.amount
                    + self.bot.already_pending(UnitTypeId.STARPORT)
                ) < 1
            ):
                # print("Start Starport before add-on")
                break
            
            if not (await self.bot.can_place_single(UnitTypeId.SUPPLYDEPOT, factory.add_on_position)):
                print("Can't build add-on, Factory lifts")
                factory(AbilityId.LIFT_FACTORY)
                break
            
            print('Build Factory Reactor')
            factory.build(UnitTypeId.FACTORYREACTOR)
        
        # Loop over each flying Factory
        for factory in self.bot.structures(UnitTypeId.FACTORYFLYING).idle:
            starports: Units = self.bot.units(UnitTypeId.STARPORT).ready + self.bot.units(UnitTypeId.STARPORTFLYING)
            starports_pending_amount = self.bot.already_pending(UnitTypeId.STARPORT)
            starports_without_reactor: Units = starports.filter(lambda starport : starport.has_add_on)
            if (
                starports_pending_amount >= 1
                or starports_without_reactor.amount >= 1
            ):
                await self.find_land_position(factory)


    async def switch_addons(self):
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
            self.bot.structures(UnitTypeId.FACTORY).ready.amount >= 1
            and self.bot.structures(UnitTypeId.FACTORYREACTOR).ready.amount >= 1
        ):
            for factory in self.bot.structures(UnitTypeId.FACTORY).ready:
                if (factory.has_add_on):
                    print ("Lift Factory")
                    factory(AbilityId.LIFT_FACTORY)

        # Handle flying Starports
        await self.handle_starport_addons()


    async def handle_starport_addons(self):
        if (self.bot.structures(UnitTypeId.STARPORTFLYING).ready.idle.amount == 0):
            return
        for flying_starport in self.bot.structures(UnitTypeId.STARPORTFLYING).ready.idle:
            reactors: Units = self.bot.structures(UnitTypeId.REACTOR)
                
            free_reactors: Units = reactors.filter(
                lambda reactor: self.bot.in_placement_grid(reactor.add_on_land_position)
            )
            if (free_reactors.amount >= 1):
                print("Land Starport")
                closest_free_reactor = free_reactors.closest_to(flying_starport)
                flying_starport(AbilityId.LAND, closest_free_reactor.add_on_land_position)
            else:
                building_factory_reactors: Units = self.bot.structures(UnitTypeId.FACTORYREACTOR).filter(
                    lambda reactor: reactor.build_progress < 1
                )
                if (building_factory_reactors):                
                    # print("Move Starport over Factory building Reactor")
                    flying_starport.move(building_factory_reactors.closest_to(flying_starport).add_on_land_position)
                else:
                    print("no free reactor")


    async def expand(self):
        next_expansion: Point2 = await self.bot.get_next_expansion()
        if (
            self.bot.can_afford(UnitTypeId.COMMANDCENTER)
            and next_expansion
        ):
            print("Expand")
            await self.bot.expand_now()


    async def build(self, unitType: UnitTypeId, position: Point2, placement_step: int = 2):
        location: Point2 = await self.bot.find_placement(unitType, near=position, placement_step=placement_step)
        if (location):
            workers = self.bot.workers.filter(
                lambda worker: (
                    (worker.is_constructing_scv and self.scv_build_progress(worker) >= 0.9)
                    or worker.orders.__len__() == 0
                    or worker.orders[0].ability.id not in AbilityBuild
                )
            )
            if (workers.amount):
                worker: Unit = workers.closest_to(location)
                worker.build(unitType, location)


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


    def scv_build_progress(self, scv: Unit):
        if (not scv.is_constructing_scv):
            return 1
        building: Unit = self.bot.structures.closest_to(scv)
        return 1 if building.is_ready else building.build_progress
    
    def is_being_constructed(self, building: Unit) -> bool:
        return (
            self.bot.workers.closest_to(building).is_constructing_scv == True
            or self.bot.workers.closest_distance_to(building) <= building.radius * math.sqrt(2)
            # or self.bot.workers.in_distance_between(structure.position, 0, structure.radius * math.sqrt(2).filter(
            #     lambda unit: unit.is_constructing_scv
            # ).amount == 0
        )

    
    async def is_buildable(self, building: Unit, points: List[Point2]):
        for point in points:
            buildable: bool = await self.bot.can_place_single(building, point)
            if not buildable:
                print(point, False)
                return False
            else:
                print(point, True)
        return True
    
    def draw_sphere_on_world(self, pos: Point2, radius: float = 2, draw_color: tuple = (255, 0, 0)):
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_sphere_out(
            Point3((pos.x, pos.y, z_height)), 
            radius, color=draw_color
        )

    def draw_text_on_world(self, pos: Point2, text: str, draw_color: tuple = (255, 102, 255), font_size: int = 14) -> None:
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_text_world(
            text,
            Point3((pos.x - 2, pos.y, z_height)),
            color=draw_color,
            size=font_size,
        )
    
    def find_closest_bottom_ramp(self, position: Point2) -> Ramp:
        return self._find_closest_ramp(position, "bottom")
    
    def find_closest_top_ramp(self, position: Point2) -> Ramp:
        return self._find_closest_ramp(position, "top")
    
    def _find_closest_ramp(self, position: Point2, extremity: Literal["top","bottom"]):
        closest_ramp: Ramp = self.bot.game_info.map_ramps[0]
        for ramp in self.bot.game_info.map_ramps:
            match extremity:
                case "top":
                    if (ramp.top_center.distance_to(position) < closest_ramp.top_center.distance_to(position)):
                        closest_ramp = ramp
                case "bottom":
                    if (ramp.bottom_center.distance_to(position) < closest_ramp.bottom_center.distance_to(position)):
                        closest_ramp = ramp
                case _:
                    print("Error : specify top or bottom of the ramp")
        return closest_ramp
        