import math
from typing import Dict, List, Tuple
from bot.buildings.build import Build
from bot.buildings.handler import BuildingsHandler
from bot.combat.combat import Combat
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.macro.macro import Macro
from bot.scout import Scout
from bot.strategy.handler import StrategyHandler
from bot.train import Train
from bot.technology.search import Search
from bot.utils.matchup import Matchup, define_matchup, get_matchup
from bot.utils.point2_functions import grid_offsets
from sc2.bot_ai import BotAI, Race
from sc2.data import Result
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from .utils.unit_tags import *

VERSION: str = "2.8.0"

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
        self.scout = Scout(self, self.expansions)

    @property
    def matchup(self) -> Matchup:
        return get_matchup(self)
    
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
            await self.expansions.set_expansion_list()
            self.builder = Build(self, self.expansions)
            self.buildings = BuildingsHandler(self, self.expansions)
            self.combat = Combat(self, self.expansions)
            self.train = Train(self, self.combat, self.expansions)
            self.macro = Macro(self, self.expansions)
            await self.macro.speed_mining.start()
            # await self.client.debug_fast_build()
            # await self.client.debug_all_resources()
            # await self.client.debug_create_unit([[UnitTypeId.REACTOR, 1, self.townhalls.random.position.towards(self._game_info.map_center, 5), 1]])
            # await self.client.debug_create_unit([[UnitTypeId.STARPORTFLYING, 1, self.townhalls.random.position.towards(self._game_info.map_center, 7), 1]])
        await self.check_surrend_condition()
        
        # General Worker management
        await self.macro.distribute_workers()
        await self.macro.mule_idle()
        await self.macro.saturate_gas()
        await self.macro.unbug_workers()
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

        # Scout with some SCV
        await self.scout.b2_against_proxy()

        # Debug stuff
        await self.combat.debug_army_orders()
        # await self.combat.debug_bases_threat()
        await self.combat.debug_bases_content()
        # await self.combat.debug_bases_distance()
        # await self.combat.debug_selection()
        # await self.combat.debug_unscouted_b2()
        await self.combat.debug_bunker_positions()
                    
    async def check_surrend_condition(self):
        landed_buildings: Units = self.structures.filter(lambda unit: unit.is_flying == False)
        if (landed_buildings.amount == 0):
            await self.client.chat_send("gg !", False)
            await self.client.leave()

    async def tag_game(self):
        await self.client.chat_send("Good Luck & Have fun !", False)
        await self.client.chat_send(f'I am Wickedbot by WickedFridge (v{VERSION})', False)
        await self.client.chat_send(f'Tag:{self.matchup}', False)
        print(f'Matchup : {self.matchup}')

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
