from __future__ import annotations
import math
from typing import List
from bot.buildings.builders.armory import Armory
from bot.buildings.builders.barracks_addon import BarracksReactor, BarracksTechlab
from bot.buildings.builders.barracks import Barracks
from bot.buildings.builders.bunker import Bunker
from bot.buildings.builders.command_center import CommandCenter
from bot.buildings.builders.ebay import Ebay
from bot.buildings.builders.factory import Factory
from bot.buildings.builders.factory_addon import FactoryReactor, FactoryTechlab
from bot.buildings.builders.fusion_core import FusionCore
from bot.buildings.builders.ghost_academy import GhostAcademy
from bot.buildings.builders.missile_turret import MissileTurret
from bot.buildings.builders.refinery import Refinery
from bot.buildings.builders.orbital_command import OrbitalCommand
from bot.buildings.builders.planetary_fortress import PlanetaryFortress
from bot.buildings.builders.starport import Starport
from bot.buildings.builders.starportreactor import StarportReactor
from bot.buildings.builders.starporttechlab import StarportTechlab
from bot.buildings.builders.supply_depot import SupplyDepot
from bot.superbot import Superbot
from bot.utils.fake_order import FakeOrder
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.unit_functions import scv_build_progress
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import production

class Builder:
    bot: Superbot
    supply_depot: SupplyDepot
    barracks: Barracks
    factory: Factory
    starport: Starport
    barracks_techlab: BarracksTechlab
    barracks_reactor: BarracksReactor
    factory_reactor: FactoryReactor
    factory_techlab: FactoryTechlab
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
        self.factory_techlab = FactoryTechlab(self)
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
                    worker.is_idle
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
    
    async def build(self, unit_type: UnitTypeId, position: Point2, radius: float, has_addon: bool = False, force_position: bool = False):
        theorical_location: Point2 = dfs_in_pathing(self.bot, position, unit_type, self.bot._game_info.map_center, radius, has_addon)
        location: Point2 = theorical_location
        if (not force_position):
            location: Point2 = await self.bot.find_placement(unit_type, near=theorical_location)
            if (location is None or not self.bot.map.influence_maps.buildings.can_build(location, unit_type)):
                await self.bot.client.chat_send(f'Tag:Build_{unit_type.name}_incorrect', False)
        workers: Units = self.worker_builders
        if (workers.amount == 0 or location is None):
            print(f'Error: no available worker or no location found to build {unit_type}')
            return
        worker: Unit = workers.closest_to(location)
        worker.build(unit_type, location)
        # Reserve the area in the influence map to prevent other buildings from getting built on top while it's being built
        # if (unit_type in production):
        #     self.bot.map.influence_maps.buildings.reserve_production(location)
        # else:
        #     self.bot.map.influence_maps.buildings.reserve_area(location, radius * 2, {unit_type})
        # TODO : replace with the correct building id
        worker.orders.append(FakeOrder(AbilityId.TERRANBUILD_COMMANDCENTER))
    
    
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