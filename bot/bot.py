from math import pi, sqrt
from typing import FrozenSet, List, Set
from sc2.bot_ai import BotAI, Race
from sc2.data import Result
from sc2.game_data import AbilityData
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit, UnitOrder
from sc2.units import Units

hq_types: List[int] = [
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.HATCHERY,
    UnitTypeId.LAIR,
    UnitTypeId.HIVE,
    UnitTypeId.NEXUS
]
worker_types: List[int] = [
    UnitTypeId.SCV,
    UnitTypeId.PROBE,
    UnitTypeId.DRONE
]
tower_types: List[int] = [
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.BUNKER,
    UnitTypeId.SPINECRAWLER
]
dont_attack: List[int] = [
    UnitTypeId.EGG,
    UnitTypeId.LARVA
]

class CompetitiveBot(BotAI):
    NAME: str = "WickedBot"
    """This bot's name"""

    RACE: Race = Race.Terran

    """This bot's Starcraft 2 race.
    Options are:
        Race.Terran
        Race.Zerg
        Race.Protoss
        Race.Random
    """
    shield_researched: bool = False
    panic_mode: bool = False

    def __init__(self) -> None:
        super().__init__()


    async def on_start(self):
        """
        This code runs once at the start of the game
        Do things here before the game starts
        """

        print("Game started")

    async def on_step(self, iteration: int):
        """
        This code runs continually throughout the game
        Populate this function with whatever your bot should do!
        """
        await self.distribute_workers()
        self.saturate_gas()
        await self.panic()
        await self.finish_buildings()
        await self.build_supply()
        await self.morph_orbitals()
        await self.drop_mules()
        await self.build_workers()
        await self.search_upgrades()
        await self.search_stim()
        await self.search_shield()
        await self.build_gas()
        await self.build_armory()
        await self.build_starport()
        await self.build_ebays()
        await self.build_barracks()
        await self.build_factory()
        await self.switch_addons()
        await self.train_medivac()
        await self.build_addons()
        await self.expand()
        await self.barracks_production()
        await self.attack()
        # await self.scout()
        self.handle_supplies()

        # if (not int(self.time) % 2  and self.time - int(self.time) <= 0.1):
        #     if (self.workers.selected):
        #         worker: Unit = self.workers.selected.random
        #         print("worker : ", worker.position)

            
        #     if (self.structures(UnitTypeId.BARRACKS).selected):
        #         barrack: Unit = self.structures(UnitTypeId.BARRACKS).selected.random
                
        #         print("rax : ", barrack.position)
        #         for addon_point in addon_points:
        #             print("addon point : ", addon_point)
        #             close_buildings: Units = self.structures.filter(lambda structure: structure.distance_to(addon_point) <= structure.footprint_radius)
        #             for building in close_buildings:
        #                 print("close_building: ", building.name, building.position, building.footprint_radius)

        #         buildable: bool = (await self.can_place_single(UnitTypeId.SUPPLYDEPOT, barrack.add_on_position))
        #         print("buildable", buildable)
        #         if buildable:
        #             print("add-on OK")
        #         else:
        #             print("add-on NOK")
                    
    def saturate_gas(self):
        # Saturate refineries
        for refinery in self.gas_buildings:
            if refinery.assigned_harvesters < refinery.ideal_harvesters:
                worker: Units = self.workers.closer_than(10, refinery)
                if worker:
                    worker.random.gather(refinery)
    
    async def finish_buildings(self):
        if (self.workers.collecting.amount == 0):
            print("no workers to finish buildings o7")
            return
        
        add_ons: List[int] = [
            UnitTypeId.BARRACKSREACTOR,
            UnitTypeId.BARRACKSTECHLAB,
            UnitTypeId.FACTORYREACTOR,
            UnitTypeId.FACTORYTECHLAB,
            UnitTypeId.STARPORTREACTOR,
            UnitTypeId.STARPORTTECHLAB
        ]
        
        incomplete_buildings: Units = self.structures.filter(
            lambda structure: (
                structure.build_progress < 1
                and structure.type_id not in add_ons
                and structure.type_id != UnitTypeId.ORBITALCOMMAND
                and (
                    self.workers.closest_to(structure).is_constructing_scv == False
                    or self.workers.closest_distance_to(structure) >= structure.radius * sqrt(2)
                )
            )
        )
        for incomplete_building in incomplete_buildings:
            closest_worker: Unit = self.workers.closest_to(incomplete_building)
            print("ordering SCV to finish", incomplete_building.name)
            closest_worker.smart(incomplete_building)
    
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

    async def build_workers(self):
        if (
            self.can_afford(UnitTypeId.SCV)
            and self.workers.amount < self.townhalls.amount * 22
            and self.workers.amount <= 84
        ) :
            if (self.orbitalTechAvailable()):
                townhalls = self.townhalls(UnitTypeId.ORBITALCOMMAND).ready.idle
            else :
                townhalls = self.townhalls(UnitTypeId.COMMANDCENTER).ready.idle
            for th in townhalls:
                    print("Train SCV")
                    th.train(UnitTypeId.SCV)

    async def build_supply(self):
        # move SCV for first depot
        workers_mining: int = self.workers.collecting.amount
        if (
            self.supply_used == 13
            and workers_mining == self.supply_used
            and self.structures(UnitTypeId.SUPPLYDEPOT).ready.amount == 0
            and self.minerals >= 50
        ):
            print("move worker for first depot")
            self.workers.random.move(self.main_base_ramp.depot_in_middle)
        
        supply_placement_positions: FrozenSet[Point2] = self.main_base_ramp.corner_depots
        depots: Units = self.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})

        # Filter locations close to finished supply depots
        if depots:
            supply_placement_positions: Set[Point2] = {
                d
                for d in supply_placement_positions if depots.closest_distance_to(d) > 1
            }
            
        if (
            self.supply_cap < 200
            and self.supply_left < 2 + self.supply_used / 10
            and self.can_afford(UnitTypeId.SUPPLYDEPOT)
            and not self.already_pending(UnitTypeId.SUPPLYDEPOT)
        ) :
            print("Build Supply Depot")
            if (len(supply_placement_positions) >= 1) :
                target_supply_location: Point2 = supply_placement_positions.pop()
                await self.build_custom(UnitTypeId.SUPPLYDEPOT, target_supply_location)
            else:
                workers: Units = self.workers.collecting
                if (workers):
                    worker: Unit = workers.furthest_to(workers.center)
                    await self.build_custom(UnitTypeId.SUPPLYDEPOT, worker.position)
    
    def handle_supplies(self):
        supplies_raised: Units = self.structures(UnitTypeId.SUPPLYDEPOT).ready
        supplies_lowered: Units = self.structures(UnitTypeId.SUPPLYDEPOTLOWERED)
        for supply in supplies_raised:
            if self.enemy_units.amount == 0 or self.enemy_units.closest_distance_to(supply) > 5:
                print("Lower Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        for supply in supplies_lowered:
            if self.enemy_units.amount >= 1 and self.enemy_units.closest_distance_to(supply) <= 5:
                print("Raise Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_RAISE)
                
    async def build_gas(self):
        gasCount: int = self.structures(UnitTypeId.REFINERY).ready.amount + self.already_pending(UnitTypeId.REFINERY)
        workers_mining: int = self.workers.collecting.amount
        if(
            self.can_afford(UnitTypeId.REFINERY)
            and gasCount <= 2 * self.townhalls.ready.amount
            and self.structures(UnitTypeId.BARRACKS).ready.amount + self.already_pending(UnitTypeId.BARRACKS) >= 1
            and workers_mining >= (gasCount + 1) * 11
            and (not self.waitingForOrbital() or self.minerals >= 225)
        ):
            for th in self.townhalls.ready:
                # Find all vespene geysers that are closer than range 10 to this townhall
                print("Build Gas")
                vgs: Units = self.vespene_geyser.closer_than(10, th)
                if (vgs.amount >= 1):
                    await self.build(UnitTypeId.REFINERY, vgs.random)
                    break

    async def build_ebays(self):
        ebay_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.ENGINEERINGBAY)
        ebays_count: int = self.structures(UnitTypeId.ENGINEERINGBAY).ready.amount + self.already_pending(UnitTypeId.ENGINEERINGBAY)

        # We want 2 ebays once we have a 3rd CC
        if (
            ebay_tech_requirement == 1
            and self.can_afford(UnitTypeId.ENGINEERINGBAY)
            and ebays_count < 2
            and self.townhalls.amount >= 3
            and not self.waitingForOrbital() 
        ) :
            print("Build EBay")
            ebay_position = await self.find_placement(UnitTypeId.ENGINEERINGBAY, near=self.townhalls.ready.center)
            if (ebay_position):
                await self.build_custom(UnitTypeId.ENGINEERINGBAY, ebay_position)
    
    async def build_armory(self):
        armory_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.ARMORY)
        upgrades_tech_requirement: float = self.already_pending_upgrade(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
        armory_count: int = self.structures(UnitTypeId.ARMORY).ready.amount + self.already_pending(UnitTypeId.ARMORY)

        # We want 1 armory once we have a +1 60% complete
        if (
            armory_tech_requirement == 1
            and upgrades_tech_requirement >= 0.6
            and self.can_afford(UnitTypeId.ARMORY)
            and armory_count == 0
            and self.townhalls.amount >= 1
        ) :
            print("Build Armory")
            armory_location = self.townhalls.closest_n_units(self.townhalls.ready.first, 2).center
            armory_position = await self.find_placement(UnitTypeId.ARMORY, near=armory_location)
            if (armory_position):
                await self.build_custom(UnitTypeId.ARMORY, armory_position)


    async def build_barracks(self):
        barracks_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.BARRACKS)
        barracksPosition: Point2 = self.main_base_ramp.barracks_correct_placement
        barracks_amount: int = self.structures(UnitTypeId.BARRACKS).ready.amount + self.already_pending(UnitTypeId.BARRACKS) + self.structures(UnitTypeId.BARRACKSFLYING).ready.amount
        cc_amount: int = self.townhalls.amount
        max_barracks: int = cc_amount ** 2 - 2 * cc_amount + 2

        # We want 1 rax for 1 base, 2 raxes for 2 bases, 5 raxes for 3 bases, 10 raxes for 4 bases
        # y = x² - 2x + 2 where x is the number of bases and y the number of raxes
        if (
            barracks_tech_requirement == 1
            and self.can_afford(UnitTypeId.BARRACKS)
            and self.already_pending(UnitTypeId.BARRACKS) < self.townhalls.amount
            and barracks_amount < max_barracks
            and not self.waitingForOrbital()
        ) :
            print("Build Barracks", barracks_amount + 1, "/", max_barracks)
            if (barracks_amount >= 1):
                cc: Unit = self.townhalls.random
                barracksPosition = cc.position.towards(self.game_info.map_center, 4)
            await self.build_custom(UnitTypeId.BARRACKS, barracksPosition)

    async def build_factory(self):
        facto_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.FACTORY)
        max_factories: int = 1
        factories_count: int = self.structures(UnitTypeId.FACTORY).ready.amount + self.structures(UnitTypeId.FACTORYFLYING).ready.amount + self.already_pending(UnitTypeId.FACTORY)

        # We want 1 factory so far
        if (
            facto_tech_requirement == 1
            and self.townhalls.amount >= 2
            and self.can_afford(UnitTypeId.FACTORY)
            and self.already_pending(UnitTypeId.FACTORY) < 1
            and not self.structures(UnitTypeId.FACTORY)
            and factories_count < max_factories
            and not self.waitingForOrbital()
        ) :
            print("Build Factory")
            cc: Unit = self.townhalls.random
            factory_position = cc.position.towards(self.game_info.map_center, 4)
            await self.build_custom(UnitTypeId.FACTORY, factory_position)

    async def build_starport(self):
        starport_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.STARPORT)
        max_starport: int = 1
        starport_count: int = self.structures(UnitTypeId.STARPORT).ready.amount + self.structures(UnitTypeId.STARPORTFLYING).ready.amount + self.already_pending(UnitTypeId.STARPORT)

        # We want 1 starport so far
        if (
            starport_tech_requirement == 1
            and self.townhalls.amount >= 2
            and self.can_afford(UnitTypeId.STARPORT)
            and self.already_pending(UnitTypeId.STARPORT) <= 2
            and not self.structures(UnitTypeId.STARPORT)
            and starport_count < max_starport
            and not self.waitingForOrbital()
        ) :
            print("Build Starport close to Factory")
            factories: Units = self.structures(UnitTypeId.FACTORY).ready
            ccs: Units = self.townhalls
            if (factories):
                starport_position = factories.random.position.towards(self.game_info.map_center, 2)
            else:
                starport_position = ccs.random.position.towards(self.game_info.map_center, 2)
            await self.build_custom(UnitTypeId.STARPORT, starport_position)

    async def build_addons(self):
        # Loop over each Barrack without an add-on
        for barrack in self.structures(UnitTypeId.BARRACKS).ready.filter(
            lambda barrack: barrack.has_add_on == False
        ):
            if (
                not barrack.is_idle
                or self.units(UnitTypeId.MARINE).ready.amount < 2
            ):
                break
            
            if not (await self.can_place_single(UnitTypeId.SUPPLYDEPOT, barrack.add_on_position)):
                print("Can't build add-on, Barracks lifts")
                barrack(AbilityId.LIFT_BARRACKS)
                
            # If we have the same number of techlabs & reactor, we build a techlab, otherwise we build a reactor
            techlab_amount = self.structures(UnitTypeId.BARRACKSTECHLAB).ready.amount + self.already_pending(UnitTypeId.BARRACKSTECHLAB)
            reactor_amount = self.structures(UnitTypeId.BARRACKSREACTOR).ready.amount + self.already_pending(UnitTypeId.BARRACKSREACTOR)
            if (
                techlab_amount <= reactor_amount):
                if (self.can_afford(UnitTypeId.BARRACKSTECHLAB)):
                    barrack.build(UnitTypeId.BARRACKSTECHLAB)
                    print("Build Techlab")
            else:
                if (self.can_afford(UnitTypeId.BARRACKSREACTOR)):
                    barrack.build(UnitTypeId.BARRACKSREACTOR)
                    print("Build Reactor")

        # Loop over each flying Barrack
        for barrack in self.structures(UnitTypeId.BARRACKSFLYING).idle:
            await self.find_land_position(barrack)

        # Loop over each Factory without an add-on
        for factory in self.structures(UnitTypeId.FACTORY).ready.filter(
            lambda factory: factory.has_add_on == False
        ):
            if (
                not factory.is_idle
                or not self.can_afford(UnitTypeId.FACTORYREACTOR)
                or self.structures(UnitTypeId.STARPORT).ready.amount < 1 and self.already_pending(UnitTypeId.STARPORT) < 1
            ):
                break
            
            if not (await self.can_place_single(UnitTypeId.SUPPLYDEPOT, factory.add_on_position)):
                print("Can't build add-on, Factory lifts")
                factory(AbilityId.LIFT_FACTORY)
            
            print('Build Factory Reactor')
            factory.build(UnitTypeId.FACTORYREACTOR)
        
        # Loop over each flying Factory
        for factory in self.structures(UnitTypeId.FACTORYFLYING).idle:
            starports: Units = self.units(UnitTypeId.STARPORT).ready + self.units(UnitTypeId.STARPORTFLYING)
            starports_pending_amount = self.already_pending(UnitTypeId.STARPORT)
            starports_without_reactor: Units = starports.filter(lambda starport : starport.has_add_on)
            if (
                starports_pending_amount == 0
                and starports_without_reactor.amount == 0
            ):
                break
            await self.find_land_position(factory)
    
    async def switch_addons(self):
        # if starport is complete and has no reactor, lift it
        if (
            self.structures(UnitTypeId.STARPORT).ready.amount >= 1
            and self.structures(UnitTypeId.STARPORTREACTOR).ready.amount < self.structures(UnitTypeId.STARPORT).ready.amount
        ):
            for starport in self.structures(UnitTypeId.STARPORT).ready:
                if (not starport.has_add_on):
                    print("Lift Starport")
                    starport(AbilityId.LIFT_STARPORT)
        
        # if factory is complete with a reactor, lift it
        if (
            self.structures(UnitTypeId.FACTORY).ready.amount >= 1
            and self.structures(UnitTypeId.FACTORYREACTOR).ready.amount >= 1
        ):
            for factory in self.structures(UnitTypeId.FACTORY).ready:
                if (factory.has_add_on):
                    print ("Lift Factory")
                    factory(AbilityId.LIFT_FACTORY)

        # Handle flying Starports
        if (self.structures(UnitTypeId.STARPORTFLYING).ready.amount >= 1):
            for flying_starport in self.structures(UnitTypeId.STARPORTFLYING).ready:
                reactors: Units = self.structures(UnitTypeId.REACTOR)
                    
                free_reactors: Units = reactors.filter(
                    lambda reactor: self.in_placement_grid(reactor.add_on_land_position)
                )
                if (free_reactors.amount >= 1):
                    # print("Land Starport")
                    closest_free_reactor = free_reactors.closest_to(flying_starport)
                    flying_starport(AbilityId.LAND, closest_free_reactor.add_on_land_position)
                else:
                    factories_building_reactor = self.structures(UnitTypeId.FACTORY).ready.filter(lambda facto: facto.is_using_ability(AbilityId.BUILD_REACTOR_FACTORY))
                    if (factories_building_reactor.amount >= 1):
                        flying_starport.move(factories_building_reactor.closest_to(flying_starport))
                    # print("no free reactor")

    async def search_stim(self):
        if (
            self.tech_requirement_progress(UpgradeId.STIMPACK) == 1
            and self.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.amount >= 1
            and self.can_afford(UpgradeId.STIMPACK)
            and not self.already_pending_upgrade(UpgradeId.STIMPACK)
        ):
            print("Search Stim")
            techlab: Unit = self.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.random
            techlab.research(UpgradeId.STIMPACK)

    async def search_shield(self):
        if (
            self.tech_requirement_progress(UpgradeId.STIMPACK) == 1
            and self.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.amount >= 1
            and self.can_afford(UpgradeId.STIMPACK)
            and self.shield_researched == False
            # and not self.already_pending_upgrade(AbilityId.RESEARCH_COMBATSHIELD)
        ):
            print("Search Shield")
            self.shield_researched = True
            techlab: Unit = self.structures(UnitTypeId.BARRACKSTECHLAB).ready.idle.random
            techlab(AbilityId.RESEARCH_COMBATSHIELD)

    async def search_upgrades(self):
        ebays: Units = self.structures(UnitTypeId.ENGINEERINGBAY).ready
        if (ebays.ready.idle.amount < 1):
            return
        
        # determine which upgrade to search
        upgrade_list: List[UpgradeId] = [
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
            UpgradeId.TERRANINFANTRYARMORSLEVEL1,
        ]
        advanced_upgrades_list: List[UpgradeId] = [
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
            UpgradeId.TERRANINFANTRYARMORSLEVEL2,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL3,
            UpgradeId.TERRANINFANTRYARMORSLEVEL3,
        ]

        # if armory is unlocked, add level 2 upgrades to the pool
        if (self.structures(UnitTypeId.ARMORY).ready.amount >= 1):
            upgrade_list = upgrade_list + advanced_upgrades_list

        for ebay in ebays.ready.idle:
            for upgrade in upgrade_list:
                if (self.can_afford(upgrade) and self.already_pending_upgrade(upgrade) == 0):
                    print("Start Upgrade : ", upgrade.name)
                    ebay.research(upgrade)
                    break

    async def train_medivac(self):
        starports: Units = self.structures(UnitTypeId.STARPORT).ready
        for starport in starports :
            if (
                self.can_afford(UnitTypeId.MEDIVAC)
                and (starport.is_idle or (starport.has_reactor and starport.orders.__len__() < 2))
            ):
                print("Train Medivac")
                starport.train(UnitTypeId.MEDIVAC)

    async def barracks_production(self):
        barracks: Units = self.structures(UnitTypeId.BARRACKS).ready
        for barrack in barracks :
            if (
                (barrack.is_idle or (barrack.has_reactor and barrack.orders.__len__() < 2))
                
            ):
                # train reaper if we don't have any
                # if (
                #     self.can_afford(UnitTypeId.REAPER)
                #     and self.units(UnitTypeId.REAPER).amount == 0
                # ):
                #     print("Train Reaper")
                #     barrack.train(UnitTypeId.REAPER)
                #     break
                
                # otherwise train marine
                if (self.can_afford(UnitTypeId.MARINE)
                    and (not self.waitingForOrbital() or self.minerals >= 200)
                ):
                    print("Train Marine")
                    barrack.train(UnitTypeId.MARINE)

    async def expand(self):
        next_expansion: Point2 = await self.get_next_expansion()
        if (
            self.can_afford(UnitTypeId.COMMANDCENTER)
            and next_expansion
        ):
            print("Expand")
            await self.expand_now()

    async def morph_orbitals(self):
        if (self.orbitalTechAvailable()):
            for cc in self.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
                if(self.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)):
                    print("Morph Orbital Command")
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def drop_mules(self):
        for orbital_command in self.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mineral_fields: Units = self.mineral_field.closer_than(10, orbital_command)
            if mineral_fields:
                mf: Unit = max(mineral_fields, key=lambda x: x.mineral_contents)
                orbital_command(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

    async def attack(self):
        marines: Units = self.units(UnitTypeId.MARINE).ready
        medivacs: Units = self.units(UnitTypeId.MEDIVAC).ready

        # TODO : Filter for only units that are on the opponent's side of the map
        army = (marines + medivacs)
        # .filter(
        #     lambda unit: unit.distance_to(self.enemy_start_locations[0]) < unit.distance_to(self.enemy_start_locations[0])
        # )

        for medivac in medivacs:
            # if not boosting, boost
            if (not medivac.has_buff(BuffId.MEDIVACSPEEDBOOST)):
                medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)

            # heal closest damaged ally
            damaged_allies: Units = self.units.filter(
                lambda unit: (
                    unit.is_biological
                    and unit.health_percentage < 1
                )
            )

            if (damaged_allies.amount >= 1):
                medivac(AbilityId.MEDIVACHEAL_HEAL,damaged_allies.closest_to(medivac))
            else:
                closest_marines: Units = marines.closest_n_units(self.enemy_start_locations[0], marines.amount // 2)
                if (closest_marines.amount >= 1):
                    medivac.move(closest_marines.center)
                elif (self.townhalls.amount >= 1):
                    medivac.move(self.townhalls.closest_to(self.enemy_start_locations[0]))

            
            # damaged_allies_close: Units = self.units.filter(
            #     lambda unit: unit.distance_to(medivac) <= 30 and unit.health_percentage < 1
            # )
            # if (damaged_allies_close.amount >= 1):
            #     very_close_allies = damaged_allies_close.filter(lambda unit: unit.distance_to(medivac) <= 5).sort(key=lambda unit: unit.health)
            #     medivac(AbilityId.MEDIVACHEAL_HEAL, damaged_allies_close.first)
            # else:
            #     closest_marines: Units = marines.closest_n_units(self.enemy_start_locations[0], marines.amount // 2)
            #     if (closest_marines.amount >= 1):
            #         medivac.move(closest_marines.center)
            #     elif (self.townhalls.amount >= 1):
            #         medivac.move(self.townhalls.closest_to(self.enemy_start_locations[0]))


        for marine in marines:            
            enemy_units = self.enemy_units.filter(lambda unit: not unit.is_structure and unit.can_be_attacked and unit.type_id not in dont_attack)
            enemy_towers = self.enemy_structures.filter(lambda unit: unit.type_id in tower_types)
            enemy_units += enemy_towers
            enemy_buildings = self.enemy_structures.filter(lambda unit: unit.can_be_attacked)

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
                and self.already_pending_upgrade(UpgradeId.STIMPACK) == 1
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
                        and closest_enemy.is_facing(marine, pi)
                        and closest_enemy.ground_range < marine.ground_range
                    ):
                        self.move_away(marine, closest_enemy)
                    else:
                        marine.move(closest_enemy)
            elif (enemy_units_in_sight) :
                marine.attack(enemy_units_in_sight.closest_to(marine))
            elif (enemy_buildings_in_range) :
                marine.attack(enemy_buildings_in_range.closest_to(marine))
            elif (marines.amount > 10) :
                # find nearest opposing townhalls
                
                enemy_workers: Units = self.enemy_units.filter(lambda unit: unit.type_id in worker_types)
                enemy_bases: Units = self.enemy_structures.filter(lambda structure: structure.type_id in hq_types)
                close_army: Units = army.closest_n_units(self.enemy_start_locations[0], army.amount // 2)

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
                    marine.attack(self.enemy_start_locations[0])
            elif (
                enemy_units_outside_of_range.amount >= 1
            ):
                distance_to_hq: float = enemy_units_outside_of_range.closest_distance_to(self.townhalls.first)
                distance_to_oppo: float = enemy_units_outside_of_range.closest_distance_to(self.enemy_start_locations[0])
                
                # meet revealed enemy outside of range if they are in our half of the map
                if (distance_to_hq < distance_to_oppo):
                    for marine in marines:
                        marine.move(enemy_units_outside_of_range.closest_to(marine))
            else:
                for marine in army:
                    if (self.townhalls.amount == 0):
                        break
                    marine.move(self.townhalls.closest_to(self.enemy_start_locations[0]))

        # if enemies in range of a CC, activate panic mode
        for cc in self.townhalls:
            if (self.enemy_units):
                if self.enemy_units.amount == 0:
                    self.panic_mode = False
                    # ask all chasing SCVs to stop
                    attacking_workers = self.workers.filter(
                        lambda unit: unit.is_attacking
                    )
                    for attacking_worker in attacking_workers:
                        attacking_worker.stop()
                    return
                closest_enemy: Unit = self.enemy_units.closest_to(cc)
                self.panic_mode = True if closest_enemy.distance_to(cc) <= 10 else False
    
    async def panic(self):
        # fill bunkers
        # for bunker in self.structures(UnitTypeId.BUNKER).ready:
        #     for marine in self.units(UnitTypeId.MARINE).closest_n_units(bunker, 4):
        #         marine(AbilityId.LOAD_BUNKER, bunker)
        if not self.panic_mode:
            return

        if self.workers.collecting.amount == 0:
            print("no workers to pull, o7")
            return

        # if every townhalls is dead, just attack the nearest unit with every worker
        if (self.townhalls.amount == 0):
            print("no townhalls left, o7")
            for worker in self.workers:
                worker.attack(self.enemy_units.closest_to(worker))
            return
        
        workers_pulled_amount: int = 0

        for cc in self.townhalls:
            # define threats in function of distance to townhalls
            # threats need to be attackable, ground units close to a CC

            enemy_threats = self.enemy_units.filter(
                lambda unit: unit.distance_to(cc) <= 10 and unit.can_be_attacked and not unit.is_flying
            )
            
            enemy_towers: Units = self.enemy_units.filter(
                lambda unit: unit.type_id in tower_types and unit.distance_to(cc) <= 20
            )

            print("panic attack : ", enemy_towers.amount, "enemy towers, ", enemy_threats.amount, "enemy units")
            # respond to canon/bunker/spine rush
            for tower in enemy_towers:
                workers: Units = self.workers.collecting.sorted_by_distance_to(tower)

                # Pull 3 workers by tower by default, less if we don't have enough
                workers_pulled: Units = workers[:3] if workers.amount >= 3 else workers

                for worker_pulled in workers_pulled:
                    worker_pulled.attack(tower)
                    workers_pulled_amount += 1

            # collecting workers close to threats should be pulled
            workers: Units = self.workers.collecting
            
            for threat in enemy_threats:
                # handle scouting worker identified as threat
                if (threat.type_id in worker_types):
                    # if no scv is already chasing
                    attacking_workers: Unit = self.workers.filter(
                        lambda unit: unit.is_attacking and unit.order_target == threat.tag
                    )
                    if (attacking_workers.amount == 0):
                        # pull 1 scv to follow it
                        attacking_worker = workers.closest_to(threat)
                        attacking_worker.attack(threat)
                        workers_pulled_amount += 1
                        break

                closest_worker: Unit = workers.closest_to(threat)
                if (closest_worker.distance_to(threat) <= 20):
                    closest_worker.attack(threat)
                    workers_pulled_amount += 1

            print(workers_pulled_amount, "workers pulled")


    def orbitalTechAvailable(self):
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9

    def waitingForOrbital(self):
        ccs: Units = self.townhalls(UnitTypeId.COMMANDCENTER).ready.filter(
            lambda cc: cc.is_using_ability(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND) == False
        )
        return self.orbitalTechAvailable() and ccs.amount >= 1

    async def build_custom(self, unitType: UnitTypeId, position: Point2, placement_step: int = 2):
        location: Point2 = await self.find_placement(unitType, near=position, placement_step=placement_step)
        if (location):
            workers = self.workers.filter(
                lambda worker: self.scv_build_progress(worker) >= 0.9
            )
            if (workers.amount):
                worker: Unit = workers.closest_to(location)
                worker.build(unitType, location)
    
    def points_to_build_addon(self, building_position: Point2) -> List[Point2]:
        """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
        addon_offset: Point2 = Point2((2.5, -0.5))
        addon_position: Point2 = building_position + addon_offset
        addon_points = [
            (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
        ]
        return addon_points

    def building_land_positions(self, sp_position: Point2) -> List[Point2]:
        """ Return all points that need to be checked when trying to land at a location where there is enough space to build an addon. Returns 13 points. """
        land_positions = [(sp_position + Point2((x, y))).rounded for x in range(-1, 2) for y in range(-1, 2)]
        return land_positions + self.points_to_build_addon(sp_position)

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

    def scv_build_progress(self, scv: Unit):
        if (not scv.is_constructing_scv):
            return 1
        building: Unit = self.structures.closest_to(scv)
        return 1 if building.is_ready else building.build_progress

    async def find_land_position(self, building: Unit):
        possible_land_positions_offset = sorted(
            (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
            key=lambda point: point.x**2 + point.y**2,
        )
        offset_point: Point2 = Point2((-0.5, -0.5))
        possible_land_positions = (building.position.rounded + offset_point + p for p in possible_land_positions_offset)
        for target_land_position in possible_land_positions:
            land_and_addon_points: List[Point2] = self.building_land_positions(target_land_position)
            if all(await self.can_place(UnitTypeId.SUPPLYDEPOT, land_and_addon_points)):
                print(building.name, " found a position to land")
                building(AbilityId.LAND, target_land_position)
                break

    async def is_buildable(self, building: Unit, points: List[Point2]):
        for point in points:
            buildable: bool = await self.can_place_single(building, point)
            if not buildable:
                print(point, False)
                return False
            else:
                print(point, True)
        return True


    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
