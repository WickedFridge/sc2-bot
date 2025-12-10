from __future__ import annotations
import math
from typing import List
from bot.buildings.armory import Armory
from bot.buildings.barracks_addon import BarracksReactor, BarracksTechlab
from bot.buildings.barracks import Barracks
from bot.buildings.bunker import Bunker
from bot.buildings.command_center import CommandCenter
from bot.buildings.ebay import Ebay
from bot.buildings.factory import Factory
from bot.buildings.factory_addon import FactoryReactor
from bot.buildings.fusion_core import FusionCore
from bot.buildings.ghost_academy import GhostAcademy
from bot.buildings.missile_turret import MissileTurret
from bot.buildings.refinery import Refinery
from bot.buildings.orbital_command import OrbitalCommand
from bot.buildings.planetary_fortress import PlanetaryFortress
from bot.buildings.starport import Starport
from bot.buildings.starportreactor import StarportReactor
from bot.buildings.starporttechlab import StarportTechlab
from bot.buildings.supply_depot import SupplyDepot
from bot.superbot import Superbot
from bot.utils.fake_order import FakeOrder
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.unit_functions import scv_build_progress
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units

class Builder:
    bot: Superbot
    supply_depot: SupplyDepot
    barracks: Barracks
    factory: Factory
    starport: Starport
    barracks_techlab: BarracksTechlab
    barracks_reactor: BarracksReactor
    factory_reactor: FactoryReactor
    starport_techlab: StarportTechlab
    starport_reactor: StarportReactor
    orbital_command: OrbitalCommand
    planetary_fortress: PlanetaryFortress
    command_center: CommandCenter
    ebay: Ebay
    armory: Armory
    ghost_academy: GhostAcademy
    fusion_core: FusionCore
    bunker: Bunker
    missile_turret: MissileTurret
    refinery: Refinery
    
    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.supply_depot = SupplyDepot(self)
        self.barracks = Barracks(self)
        self.factory = Factory(self)
        self.starport = Starport(self)
        self.barracks_techlab = BarracksTechlab(self)
        self.barracks_reactor = BarracksReactor(self)
        self.factory_reactor = FactoryReactor(self)
        self.starport_techlab = StarportTechlab(self)
        self.starport_reactor = StarportReactor(self)
        self.orbital_command = OrbitalCommand(self)
        self.command_center = CommandCenter(self)
        self.planetary_fortress = PlanetaryFortress(self)
        self.ebay = Ebay(self)
        self.armory = Armory(self)
        self.ghost_academy = GhostAcademy(self)
        self.fusion_core = FusionCore(self)
        self.bunker = Bunker(self)
        self.missile_turret = MissileTurret(self)
        self.refinery = Refinery(self)

    @property
    def worker_builders(self) -> Units:
        return self.bot.workers.filter(
            lambda worker: (
                (
                    worker.is_carrying_resource == False
                    or self.bot.time <= 200
                )
                and worker.is_attacking == False
                and (
                    len(worker.orders) == 0
                    or not worker.is_constructing_scv
                    or (
                        worker.is_constructing_scv
                        and scv_build_progress(self.bot, worker) >= 0.95
                        and worker.orders[0].target is not None
                        and isinstance(worker.orders[0].target, Point2)
                        and worker.orders[0].target.distance_to(worker.position) <= 2
                    )
                )
            )
        )
    
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

    
    async def build(self, unit_type: UnitTypeId, position: Point2, radius: float, has_addon: bool = False):
        theorical_location: Point2 = dfs_in_pathing(self.bot, position, self.bot._game_info.map_center, radius, has_addon)
        location: Point2 = await self.bot.find_placement(unit_type, near=theorical_location)
        if (location is None or not self.bot.map.in_building_grid(location)):
            await self.bot.client.chat_send(f'Tag:Build_{unit_type}_incorrect', False)
        workers: Units = self.worker_builders
        if (workers.amount == 0 or location is None):
            print(f'Error: no available worker or no location found to build {unit_type}')
            return
        worker: Unit = workers.closest_to(location)
        worker.build(unit_type, location)
        # TODO : replace with the correct building id
        worker.orders.append(FakeOrder(AbilityId.TERRANBUILD_COMMANDCENTER))


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

    
    def is_being_constructed(self, building: Unit) -> bool:
        return (
            self.bot.workers.closest_to(building).is_constructing_scv == True
            or self.bot.workers.closest_distance_to(building) <= building.radius * math.sqrt(2)
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