import math
from typing import List, Tuple
from bot.buildings.build import Build
from bot.buildings.handler import BuildingsHandler
from bot.combat.combat import Combat
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.macro.macro import Macro
from bot.strategy.handler import StrategyHandler
from bot.train import Train
from bot.technology.search import Search
from bot.utils.races import Races
from sc2.bot_ai import BotAI, Race
from sc2.data import Result
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from .utils.unit_tags import *

VERSION: str = "2.3.4"

class WickedBot(BotAI):
    NAME: str = "WickedBot"
    RACE: Race = Race.Terran
    
    builder: Build
    buildings: BuildingsHandler
    search: Search
    combat: Combat
    train: Train
    macro: Macro
    strategy: StrategyHandler
    expansions: Expansions

    def __init__(self) -> None:
        super().__init__()
        self.expansions = Expansions(self)
        self.builder = Build(self, self.expansions)
        self.buildings = BuildingsHandler(self, self.expansions)
        self.search = Search(self)
        self.combat = Combat(self, self.expansions)
        self.train = Train(self, self.combat, self.expansions)
        self.macro = Macro(self, self.expansions)
        self.strategy = StrategyHandler(self)
        self.expansions = Expansions(self)

    async def on_start(self):
        """
        This code runs once at the start of the game
        Do things here before the game starts
        """

        print(f'Game started, version {VERSION}')
        await self.macro.split_workers()
    
    async def on_step(self, iteration: int):
        """
        This code runs continually throughout the game
        Populate this function with whatever your bot should do!
        """
        if (iteration < 1):
            return
        # General Game Stuff
        if (iteration == 1):
            await self.tag_game()
            await self.macro.speed_mining.start()
            await self.expansions.set_expansion_list()
            self.builder = Build(self, self.expansions)
            self.buildings = BuildingsHandler(self, self.expansions)
            self.combat = Combat(self, self.expansions)
            self.train = Train(self, self.combat, self.expansions)
            self.macro = Macro(self, self.expansions)
            # await self.client.debug_all_resources()
            # await self.client.debug_create_unit([[UnitTypeId.FACTORYFLYING, 1, self.townhalls.random.position.towards(self._game_info.map_center, 5), 1]])
            # await self.client.debug_create_unit([[UnitTypeId.STARPORTFLYING, 1, self.townhalls.random.position.towards(self._game_info.map_center, 7), 1]])
        await self.check_surrend_condition()
        
        # General Worker management
        await self.distribute_workers()
        await self.macro.mule_idle()
        await self.macro.saturate_gas()
        await self.macro.speed_mining.execute()
        
        # Assement of the situation
        await self.combat.detect_enemy_army()
        await self.macro.update_threat_level()
        await self.strategy.update_situation()
        
        # Specific Worker Management
        await self.macro.workers_response_to_threat()
        await self.buildings.repair_buildings()
        await self.buildings.cancel_buildings()
        await self.builder.finish_construction()

        self.expansion_locations
        # Control buildings
        await self.buildings.drop_mules()
        await self.builder.switch_addons()
        await self.buildings.handle_supplies()
        await self.buildings.lift_orbital()
        await self.buildings.land_orbital()
        
        # Spend Money
        await self.builder.supplies()
        await self.builder.bunker()
        await self.buildings.morph_orbitals()        
        await self.train.workers()
        await self.search.tech()
        await self.builder.gas()
        await self.builder.armory()
        await self.builder.starport()
        await self.train.medivac()
        await self.builder.ebays()
        await self.builder.factory()
        await self.builder.barracks()
        await self.builder.addons()
        await self.builder.build_expand()
        await self.train.infantry()
        
        # Control Attacking Units
        await self.combat.select_orders(iteration, self.strategy.situation)
        await self.combat.execute_orders()
        await self.combat.handle_bunkers()

        # Debug stuff
        await self.combat.debug_army_orders()
        await self.combat.debug_bases_threat()
        await self.combat.debug_selection()

        last_expansion: Expansion = self.expansions.last
        for expansion in self.expansions.taken:
            is_last: bool = last_expansion and expansion.position == last_expansion.position
            text: str = f'[LAST : {is_last}] : {expansion.distance_from_main}'
            self.combat.draw_text_on_world(expansion.position, text)
        
        # TODO
        # await self.scout()
                    
    async def check_surrend_condition(self):
        landed_buildings: Units = self.structures.filter(lambda unit: unit.is_flying == False)
        if (landed_buildings.amount == 0):
            await self.client.chat_send("gg !", False)
            await self.client.leave()
    
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

    async def tag_game(self):
        await self.client.chat_send("Good Luck & Have fun !", False)
        await self.client.chat_send(f'I am Wickedbot by WickedFridge (v{VERSION})', False)
        game_races: List[str] = [
            Races[self.game_info.player_races[1]],
            Races[self.game_info.player_races[2]],
        ]
        game_races.sort()
        await self.client.chat_send(f'Tag:{game_races[0]}v{game_races[1]}', False)

    def orbitalTechAvailable(self):
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9

    def waitingForOrbital(self):
        ccs: Units = self.townhalls(UnitTypeId.COMMANDCENTER).ready.filter(
            lambda cc: cc.is_using_ability(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND) == False
        )
        return self.orbitalTechAvailable() and ccs.amount >= 1

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: int):
        pass
    
    async def on_unit_destroyed(self, unit_tag: int):
        self.combat.unit_died(unit_tag)

    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
