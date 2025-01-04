from math import pi, sqrt
from typing import FrozenSet, List, Set
from bot.buildings.build import Build
from bot.buildings.handler import BuildingsHandler
from bot.combat.combat import Combat
from bot.train import Train
from bot.technology.search import Search
from sc2.bot_ai import BotAI, Race
from sc2.data import Result
from sc2.game_data import AbilityData, UpgradeData
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit, UnitOrder
from sc2.units import Units
from .utils.unit_tags import *
from sc2.dicts.unit_abilities import UNIT_ABILITIES


class WickedBot(BotAI):
    NAME: str = "WickedBot"
    RACE: Race = Race.Terran
    panic_mode: bool = False
    
    builder: Build
    buildings: BuildingsHandler
    search: Search
    combat: Combat
    train: Train

    def __init__(self) -> None:
        super().__init__()
        self.builder = Build(self)
        self.buildings = BuildingsHandler(self)
        self.search = Search(self)
        self.combat = Combat(self)
        self.train = Train(self, self.combat)

    async def on_start(self):
        """
        This code runs once at the start of the game
        Do things here before the game starts
        """

        print("Game started")
        await self.chat_send("Good Luck & Have fun !")
        # await self.client.debug_create_unit([[UnitTypeId.ARMORY, 1, self.townhalls.random.position.towards(self._game_info.map_center, 3), 1]])
        # await self.client.debug_all_resources()

    async def on_step(self, iteration: int):
        """
        This code runs continually throughout the game
        Populate this function with whatever your bot should do!
        """
        await self.distribute_workers()
        await self.saturate_gas()
        await self.combat.detect_enemy_army()
        await self.combat.detect_threat()
        await self.combat.workers_response_to_threat()
        # await self.combat.detect_panic()
        # await self.combat.pull_workers()
        await self.buildings.repair_buildings()
        await self.builder.finish_construction()
        await self.builder.supplies()
        await self.builder.bunker()
        await self.buildings.morph_orbitals()
        await self.buildings.drop_mules()
        await self.train.workers()
        await self.search.tech()
        await self.builder.gas()
        await self.builder.armory()
        await self.builder.starport()
        await self.builder.ebays()
        await self.builder.barracks()
        await self.builder.factory()
        await self.builder.switch_addons()
        await self.train.medivac()
        await self.builder.addons()
        await self.builder.expand()
        await self.train.infantry()
        await self.combat.select_orders()
        await self.combat.execute_orders()
        await self.combat.handle_bunkers()
        # await self.combat.debug_colorize_army()
        # await self.combat.debug_colorize_bases()
        # await self.scout()
        await self.buildings.handle_supplies()

        Armories: Units = self.structures(UnitTypeId.ARMORY).filter(lambda unit: unit.is_selected)
        if (Armories.amount >= 1 and round(self.time) % 2 == 0):
            Armory: Unit = Armories.random
            print("Armory", Armory)
            print("Orders", Armory.orders)
            Armory.research(UpgradeId.TERRANVEHICLEARMORSVANADIUMPLATINGLEVEL1)
            # Armory(AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1)
                    
    async def saturate_gas(self):
        # Saturate refineries
        for refinery in self.gas_buildings:
            if refinery.assigned_harvesters < refinery.ideal_harvesters:
                worker: Units = self.workers.gathering.closer_than(10, refinery)
                if worker:
                    worker.random.gather(refinery)
    
    async def scout(self):
        # Use the reaper to scout
        if(self.units(UnitTypeId.REAPER).amount == 0):
            return
        
        reaper: Unit = self.units(UnitTypeId.REAPER).random

        # if enemy unit in range, move away
        if (self.enemy_units.amount >= 1):
            closest_enemy_unit: Unit = self.enemy_units.closest_to(reaper)
            if (
                closest_enemy_unit.distance_to(reaper) <= 7
                and closest_enemy_unit.can_attack_ground
            ):
                print("distance between reaper and", closest_enemy_unit.name, ":", closest_enemy_unit.distance_to(reaper))
                self.move_away(reaper, closest_enemy_unit)

        # otherwise, move to a random spot around the enemy start location
        else:
            reaper.move(self.enemy_start_locations[0])

        # # Scout every 30 seconds with closest marine
        # if (not int(self.time) % 30  and self.time - int(self.time) <= 0.1):

        #     # determine what we have to scout
        #     possible_enemy_expansion_positions: List[Point2] = self.expansion_locations_list.sort(
        #         key = lambda position: position.distance_to(self.enemy_start_locations[0])
        #     )[:self.townhalls.amount]
            
        #     for position_to_scout in possible_enemy_expansion_positions:
        #         # determine which unit is our scouting unit
        #         if (self.units(UnitTypeId.MARINE).amount >= 1):
        #             # select the unit that is the closest to stuff we don't know
        #             closest_marine: Unit = self.units(UnitTypeId.MARINE).closest_to(position_to_scout)
        #             print("Send Marine to scout")
        #             closest_marine.move(position_to_scout)


    def orbitalTechAvailable(self):
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9

    def waitingForOrbital(self):
        ccs: Units = self.townhalls(UnitTypeId.COMMANDCENTER).ready.filter(
            lambda cc: cc.is_using_ability(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND) == False
        )
        return self.orbitalTechAvailable() and ccs.amount >= 1

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: int):
        return 
    
    async def on_unit_destroyed(self, unit_tag: int):
        self.combat.unit_died(unit_tag)

    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
