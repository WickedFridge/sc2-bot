from time import perf_counter
from typing import Awaitable, Callable, List, override
from bot.army_composition.army_composition_manager import get_composition_manager
from bot.buildings.builder import Builder
from bot.buildings.handler import BuildingsHandler
from bot.combat.combat import Combat
from bot.debug import Debug
from bot.macro.expansion_manager import Expansions, get_expansions
from bot.macro.macro import Macro
from bot.macro.map import MapData, get_map
from bot.macro.resources import Resources
from bot.scout import Scout
from bot.scouting.scouting import Scouting, get_scouting
from bot.strategy.handler import StrategyHandler
from bot.superbot import Superbot
from bot.technology.search import Search
from bot.units.trainer import Trainer
from bot.utils.matchup import Matchup, get_matchup
from sc2.bot_ai import Race
from sc2.data import Result
from sc2.unit import Unit
from sc2.units import Units
from .utils.unit_tags import *

VERSION: str = "5.6.0"

class WickedBot(Superbot):
    NAME: str = "WickedBot"
    RACE: Race = Race.Terran
    
    builder: Builder
    buildings: BuildingsHandler
    search: Search
    combat: Combat
    trainer: Trainer
    macro: Macro
    strategy: StrategyHandler
    debug: Debug
    structures_memory: Units
    opponent_random: bool = False
    tag_to_update: bool = False

    def __init__(self) -> None:
        super().__init__()
        self.builder = Builder(self)
        self.buildings = BuildingsHandler(self)
        self.search = Search(self)
        self.combat = Combat(self)
        self.trainer = Trainer(self, self.combat)
        self.macro = Macro(self)
        self.strategy = StrategyHandler(self)
        self.scout = Scout(self)
        self.debug = Debug(self)
        self.structures_memory: Units = Units([], self)

    @override
    @property
    def matchup(self) -> Matchup:
        matchup: Matchup = get_matchup(self)
        if (matchup == Matchup.TvR):
            self.opponent_random = True
        if (self.opponent_random == True and matchup != Matchup.TvR):
            self.tag_to_update = True
            self.opponent_random = False
        return matchup
    
    @override
    @property
    def expansions(self) -> Expansions:
        return get_expansions(self)
    
    @override
    @property
    def map(self) -> MapData:
        return get_map(self)

    @override
    @property
    def scouting(self) -> Scouting:
        return get_scouting(self)

    @override
    @property
    def composition_manager(self):
        return get_composition_manager(self)

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
            await self.greetings()
            await self.tag_game()
            await self.expansions.set_expansion_list()
            self.map.initialize()
            await self.macro.speed_mining.start()

            # await self.client.debug_fast_build()
            # await self.client.debug_all_resources()
            # await self.client.debug_show_map()
            # await self.client.debug_control_enemy()
            # await self.client.debug_upgrade()
            # await self.client.debug_create_unit([[UnitTypeId.ENGINEERINGBAY, 1, self._game_info.map_center.towards(self.townhalls.random.position, 3), 1]])
            # await self.client.debug_create_unit([[UnitTypeId.MARINE, 12, self._game_info.map_center.towards(self.townhalls.random.position, 3), 1]])
            # await self.client.debug_create_unit([[UnitTypeId.GHOST, 20, self._game_info.map_center.towards(self.townhalls.random.position, 3), 1]])
            # await self.client.debug_create_unit([[UnitTypeId.ROACH, 14, self._game_info.map_center.towards(self.enemy_start_locations[0], 1.5), 2]])
            # await self.client.debug_create_unit([[UnitTypeId.ROACH, 6, self._game_info.map_center.towards(self.enemy_start_locations[0], 2), 2]])
            # await self.client.debug_create_unit([[UnitTypeId.HYDRALISK, 6, self._game_info.map_center.towards(self.enemy_start_locations[0], 2.5), 2]])
        start_time: float = perf_counter()
        await self.check_surrend_condition()
        # Update random tag
        if (self.tag_to_update):
            await self.tag_game()
        
        # Update Building grid and last known enemy positions
        self.structures_memory = self.structures.copy()
        await self.map.update()
        
        # General Worker management
        await self.macro.distribute_workers(iteration)
        await self.macro.mule_idle()
        await self.macro.saturate_gas()
        await self.macro.unbug_workers()
        await self.macro.speed_mining.execute()
        
        # Assement of the situation
        self.scouting.detect_enemy_army()
        await self.scouting.detect_enemy_upgrades()
        await self.macro.update_threat_level()
        await self.strategy.update_situation()
        self.composition_manager.calculate_composition()
        
        # Specific Worker Management
        await self.macro.workers_response_to_threat()
        await self.buildings.repair_buildings()
        await self.buildings.cancel_buildings()
        await self.buildings.finish_construction()
        await self.builder.supply_depot.move_worker_first()

        # Control buildings
        await self.buildings.drop_mules()
        await self.buildings.scan()
        await self.buildings.handle_supplies()
        await self.buildings.lift_townhalls()
        await self.buildings.land_townhalls()
        await self.buildings.reposition_buildings()
        await self.buildings.salvage_bunkers()
        
        # Spend Money
        
        money_spender_names: List[str] = [
            'orbital_command',
            'supply_depot',
            'workers',
            'barracks_techlab',
            'barracks_reactor',
            'factory_reactor',
            'tech',
            'armory',
            'medivac',
            'infantry',
            'ebay',
            'bunker',
            'starport',
            'factory',
            'barracks',
            'refinery',
            'command_center',
        ]

        money_spenders: List[Callable[[Resources], Awaitable[Resources]]] = []
        money_spenders.extend([
            # basic economy
            self.builder.orbital_command.upgrade,
            self.builder.supply_depot.build,
            self.trainer.scv.train,
            self.builder.refinery.build,
        ])
        money_spenders.extend([
            # add ons
            self.builder.barracks_techlab.build,
            self.builder.barracks_reactor.build,
            self.builder.factory_reactor.build,
            self.builder.starport_techlab.build,
            self.builder.starport_reactor.build,
        ])
        money_spenders.extend([
            # defense
            self.builder.planetary_fortress.upgrade,
            self.builder.bunker.build,
            self.builder.missile_turret.build,
        ])
        money_spenders.extend([
            # very important tech
            self.search.tech_primary,
        ])
        money_spenders.extend(self.trainer.ordered_army_trainers)
        money_spenders.extend([
            # army
            self.trainer.medivac.train,
            self.trainer.ghost.train,
            self.trainer.marauder.train,
            self.trainer.marine.train,
        ])
        money_spenders.extend([
            # advanced tech
            self.search.tech_secondary,
            self.builder.armory.build,
        ])
        money_spenders.extend([
            # production buildings
            self.builder.starport.build,
            self.builder.factory.build,
            self.builder.barracks.build,
        ])
        money_spenders.extend([
            # late game tech
            self.builder.ebay.build,
            self.builder.ghost_academy.build,
            self.builder.fusion_core.build,
        ])
        money_spenders.extend([
            # expands
            self.builder.command_center.build,
        ])
        
        resources: Resources = Resources.from_tuples(
            (self.minerals, False),
            (self.vespene, False)
        )
        for i, money_spender in enumerate(money_spenders):
            if (resources.is_short_both):
                break
            resources = await money_spender(resources)


        
        # Control Attacking Units
        await self.combat.select_orders(iteration, self.strategy.situation)
        await self.combat.execute_orders()
        await self.combat.handle_bunkers()

        # Scout with some SCV
        await self.scout.b2_against_proxy()

        # Debug stuff
        
        # await self.debug.drop_path()
        await self.combat.debug_drop_target()
        # await self.debug.unscouted_b2()
        # await self.debug.colorize_bunkers()
        # await self.debug.placement_grid()
        # await self.debug.pathing_grid()
        # await self.debug.building_grid()
        await self.combat.debug_army_orders()
        # await self.macro.debug_bases_threat()
        # await self.debug.bases_content()
        # await self.debug.bases_bunkers()
        # await self.debug.bases_distance()
        # await self.debug.selection()
        # self.macro.supply_block_update()
        # await self.debug.invisible_units()
        # await self.debug.loaded_stuff(iteration)
        # await self.debug.bunker_positions()
        # await self.debug.wall_placement()
        await self.debug.spawn_test_units()
        await self.debug.composition_manager()
        await self.debug.composition_priorities()
        end_time: float = perf_counter()
        
        self.client.debug_text_screen(
            f'Step Time: {(end_time - start_time)*1000:.2f} ms',
            (0.01, 0.01),
        )
        
                    
    async def check_surrend_condition(self):
        landed_buildings: Units = self.structures.filter(lambda unit: unit.is_flying == False)
        if (landed_buildings.amount == 0):
            await self.client.chat_send("gg !", False)
            await self.client.leave()

    async def greetings(self):
        await self.client.chat_send("Good Luck & Have fun !", False)
        await self.client.chat_send(f'I am Wickedbot by WickedFridge (v{VERSION})', False)
    
    async def tag_game(self):
        await self.client.chat_send(f'Tag:{self.matchup}', False)
        print(f'Matchup : {self.matchup}')
        self.tag_to_update = False

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: int):
        pass
    
    async def on_unit_destroyed(self, unit_tag: int):
        self.scouting.unit_died(unit_tag)
        if (unit_tag in self.structures_memory.tags):
            print('structure destroyed - Removing it from grid')
            dead_structure: Unit = self.structures_memory.find_by_tag(unit_tag)
            self.map.update_building_grid(dead_structure, enable=True)


    async def on_building_construction_started(self, unit):
        self.map.update_building_grid(unit)

    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
