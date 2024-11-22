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
        await self.build_supply()
        await self.morph_orbitals()
        await self.drop_mules()
        await self.build_workers()
        await self.build_gas()
        await self.train_medivac()
        await self.build_starport()
        await self.build_ebays()
        await self.build_barracks()
        await self.build_factory()
        await self.switch_addons()
        await self.build_addons()
        await self.search_stim()
        await self.search_shield()
        await self.search_upgrades()
        await self.train_marine()
        await self.attack()
        await self.expand()
        self.lower_supplies()

        # if (not int(self.time) % 2  and self.time - int(self.time) <= 0.1):
        #     workers: Units = self.workers.selected
        #     if (workers):
        #         scv: Unit = workers.random
        #         print("SCV is building", scv.is_constructing_scv)
        #         print("build progress", self.scv_build_progress(scv))

    def saturate_gas(self):
        # Saturate refineries
        for refinery in self.gas_buildings:
            if refinery.assigned_harvesters < refinery.ideal_harvesters:
                worker: Units = self.workers.closer_than(10, refinery)
                if worker:
                    worker.random.gather(refinery)
    
    async def build_workers(self):
        if (
            self.can_afford(UnitTypeId.SCV)
            and self.workers.amount < self.townhalls.amount * 22
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
        workers_mining: int = self.workers.gathering.amount + self.workers.returning.amount
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
                workers: Units = self.workers.gathering
                worker: Unit = workers.furthest_to(workers.center)
                await self.build_custom(UnitTypeId.SUPPLYDEPOT, worker.position)
    
    def lower_supplies(self):
        supplies: Units = self.structures(UnitTypeId.SUPPLYDEPOT).ready
        for supply in supplies :
            print("Lower Supply Depot")
            supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

    async def build_gas(self):
        gasCount: int = self.structures(UnitTypeId.REFINERY).amount
        workers_mining: int = self.workers.gathering.amount + self.workers.returning.amount
        if(
            self.can_afford(UnitTypeId.REFINERY)
            and self.structures(UnitTypeId.REFINERY).amount <= 2 * self.townhalls.ready.amount
            and self.structures(UnitTypeId.BARRACKS).amount >= 1
            and workers_mining >= (gasCount + 1) * 11
            and (not self.waitingForOrbital() or self.minerals >= 225)
        ):
            for th in self.townhalls.ready:
                # Find all vespene geysers that are closer than range 10 to this townhall
                print("Build Gas")
                vgs: Units = self.vespene_geyser.closer_than(10, th)
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
                workers = self.workers.filter(
                    # lambda worker: worker.is_constructing_scv == False
                    lambda worker: worker.is_idle or worker.is_gathering or worker.is_collecting
                )
                worker: Unit = workers.closest_to(ebay_position)
                worker.build(UnitTypeId.ENGINEERINGBAY, ebay_position)


    async def build_barracks(self):
        barracks_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.BARRACKS)
        barracksPosition: Point2 = self.main_base_ramp.barracks_correct_placement
        barracks_amount: int = self.structures(UnitTypeId.BARRACKS).amount + self.structures(UnitTypeId.BARRACKSFLYING).amount
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
        factories_count: int = self.structures(UnitTypeId.FACTORY).amount + self.structures(UnitTypeId.FACTORYFLYING).amount

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
        starport_count: int = self.structures(UnitTypeId.STARPORT).amount + self.structures(UnitTypeId.STARPORTFLYING).amount

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
            
            addon_points = self.points_to_build_addon(barrack.position)
            if not all(
                self.in_map_bounds(addon_point) and self.in_placement_grid(addon_point)
                and self.in_pathing_grid(addon_point) for addon_point in addon_points
            ):
                print("Can't build add-on, Barracks lifts")
                barrack(AbilityId.LIFT_BARRACKS)
                
            # If we have the same number of techlabs & reactor, we build a techlab, otherwise we build a reactor
            if (
                self.structures(UnitTypeId.BARRACKSTECHLAB).amount <= self.structures(UnitTypeId.BARRACKSREACTOR).amount):
                if (self.can_afford(UnitTypeId.BARRACKSTECHLAB)):
                    barrack.build(UnitTypeId.BARRACKSTECHLAB)
                    print("Build Techlab")
            else:
                if (self.can_afford(UnitTypeId.BARRACKSREACTOR)):
                    barrack.build(UnitTypeId.BARRACKSREACTOR)
                    print("Build Reactor")

        # Loop over each flying Barrack
        for barrack in self.structures(UnitTypeId.BARRACKSFLYING).idle:
            possible_land_positions_offset = sorted(
                (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
                key=lambda point: point.x**2 + point.y**2,
            )
            offset_point: Point2 = Point2((-0.5, -0.5))
            possible_land_positions = (barrack.position.rounded + offset_point + p for p in possible_land_positions_offset)
            for target_land_position in possible_land_positions:
                land_and_addon_points: List[Point2] = self.building_land_positions(target_land_position)
                if all(
                    self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos)
                    and self.in_pathing_grid(land_pos) for land_pos in land_and_addon_points
                ):
                    print("Barracks found a position to land")
                    barrack(AbilityId.LAND, target_land_position)
                    break

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
            
            addon_points = self.points_to_build_addon(factory.position)
            if not all(
                self.in_map_bounds(addon_point) and self.in_placement_grid(addon_point)
                and self.in_pathing_grid(addon_point) for addon_point in addon_points
            ):
                print("Can't build add-on, Factory lifts")
                factory(AbilityId.LIFT_FACTORY)
                break
            
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
            
            possible_land_positions_offset = sorted(
                (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
                key=lambda point: point.x**2 + point.y**2,
            )
            offset_point: Point2 = Point2((-0.5, -0.5))
            possible_land_positions = (factory.position.rounded + offset_point + p for p in possible_land_positions_offset)
            for target_land_position in possible_land_positions:
                land_and_addon_points: List[Point2] = self.building_land_positions(target_land_position)
                if all(
                    self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos)
                    and self.in_pathing_grid(land_pos) for land_pos in land_and_addon_points
                ):
                    print("Factory found a position to land")
                    factory(AbilityId.LAND, target_land_position)
                    break
    
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
                if (reactors.amount == 0):
                    break
                    
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
        
        ebay: Unit = ebays.idle.random
        if (not ebay):
            return
        
        # determine which upgrade to search
        if (
            self.can_afford(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
            and not self.already_pending_upgrade(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
        ):
            print("Start +1/+0")
            ebay.research(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
        elif (
            self.can_afford(UpgradeId.TERRANINFANTRYARMORSLEVEL1)
            and not self.already_pending_upgrade(UpgradeId.TERRANINFANTRYARMORSLEVEL1)
        ):
            print("Start +0/+1")
            ebay.research(UpgradeId.TERRANINFANTRYARMORSLEVEL1)

    async def train_medivac(self):
        starports: Units = self.structures(UnitTypeId.STARPORT).ready
        for starport in starports :
            if (
                self.can_afford(UnitTypeId.MEDIVAC)
                and (starport.is_idle or (starport.has_reactor and starport.orders.__len__() < 2))
            ):
                print("Train Medivak")
                starport.train(UnitTypeId.MEDIVAC)

    async def train_marine(self):
        barracks: Units = self.structures(UnitTypeId.BARRACKS).ready
        for barrack in barracks :
            if (
                self.can_afford(UnitTypeId.MARINE)
                and (barrack.is_idle or (barrack.has_reactor and barrack.orders.__len__() < 2))
                and (not self.waitingForOrbital() or self.minerals >= 200)
            ):
                print("Train Marine")
                barrack.train(UnitTypeId.MARINE)


    async def expand(self):
        next_expansion: Point2 = await self.get_next_expansion()
        if (
            self.can_afford(UnitTypeId.COMMANDCENTER)
            # and self.townhalls.ready.amount + self.already_pending(UnitTypeId.COMMANDCENTER) < 3
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
        for oc in self.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mfs: Units = self.mineral_field.closer_than(10, oc)
            if mfs:
                mf: Unit = max(mfs, key=lambda x: x.mineral_contents)
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

    async def attack(self):
        marines: Units = self.units(UnitTypeId.MARINE).ready
        medivaks: Units = self.units(UnitTypeId.MEDIVAC).ready

        army = marines + medivaks
        for medivak in medivaks:
            # if not boosting, boost
            if (not medivak.has_buff(BuffId.MEDIVACSPEEDBOOST)):
                medivak(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
            
            # if no energy, no healing
            if (medivak.energy == 0):
                break

            # if damaged units in sight, heal them
            damaged_allies_close: Units = self.units.filter(
                lambda unit: unit.distance_to(medivak) <= 15 and unit.health_percentage < 1
            )
            if (damaged_allies_close.amount >= 1):
                medivak(AbilityId.MEDIVACHEAL_HEAL, damaged_allies_close.random)
            else:
                closest_marines: Units = marines.closest_n_units(self.enemy_start_locations[0], 5)
                if (closest_marines.amount >= 1):
                    medivak.move(closest_marines.center)
                else:
                    medivak.move(self.townhalls.closest_to(self.enemy_start_locations[0]))


        for marine in marines:
            #If units in sight, should be stimmed
            enemies_in_sight: Units = self.enemy_units.filter(
                lambda unit: unit.distance_to(marine) <= 10 and unit.can_be_attacked
            )
            if (
                enemies_in_sight
                and self.already_pending_upgrade(UpgradeId.STIMPACK) == 1
                and not marine.has_buff(BuffId.STIMPACK)
            ):
                # print("Stim")
                marine(AbilityId.EFFECT_STIM_MARINE)
            
            #If units in range, attack the one with the least HPs, closest if tied (don't forget to stim first if not)
            enemies: Units = self.enemy_units | self.enemy_structures
            enemy_ground_units_in_range: Units = enemies.filter(
                lambda unit: marine.target_in_range(unit) and not unit.is_structure and unit.can_be_attacked
            )
            enemy_ground_units_outside_of_range: Units = enemies.filter(
                lambda unit: not marine.target_in_range(unit) and not unit.is_structure and unit.can_be_attacked
            )
            
            enemy_ground_buildings: Units = enemies.filter(
                lambda unit: marine.target_in_range(unit) and unit.is_structure and unit.can_be_attacked
            )

            if (enemy_ground_units_in_range) :
                enemy_ground_units_in_range.sort(
                    key=lambda unit: unit.health
                )
                if (marine.weapon_ready):
                    marine.attack(enemy_ground_units_in_range[0])
                else:
                    closest_enemy: Unit = enemy_ground_units_in_range.closest_to(marine)
                    if(closest_enemy.can_attack and closest_enemy.ground_range < marine.ground_range):
                        self.move_away(marine, closest_enemy)
            elif (enemy_ground_buildings) :
                    marine.attack(enemy_ground_buildings.closest_to(marine))
            elif (army.amount > 15) :
                    marine.attack(self.enemy_start_locations[0])
            elif (
                enemy_ground_units_outside_of_range.amount >= 1
            ):
                distance_to_hq: float = enemy_ground_units_outside_of_range.closest_distance_to(self.townhalls.first)
                distance_to_oppo: float = enemy_ground_units_outside_of_range.closest_distance_to(self.enemy_start_locations[0])
                # meet revealed enemy outside of range if they are in our half of the map
                if (distance_to_hq < distance_to_oppo):
                    for marine in army:
                        marine.move(enemy_ground_units_outside_of_range.closest_to(marine))
            else:
                # find nearest opposing townhalls
                self.enemy_structures.filter(lambda structure: structure)
                for marine in army:
                    marine.move(self.townhalls.closest_to(self.enemy_start_locations[0]))
                    
    def orbitalTechAvailable(self):
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) >= 0.9

    def waitingForOrbital(self):
        ccs: Units = self.townhalls(UnitTypeId.COMMANDCENTER).ready.filter(
            lambda cc: cc.is_using_ability(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND) == False
        )
        return self.orbitalTechAvailable() and ccs.amount >= 1

    async def build_custom(self, unitType: UnitTypeId, position: Point2, placement_step: int = 2):
        # addon_place: bool = (
        #     unitType == UnitTypeId.BARRACKS
        #     or unitType == UnitTypeId.FACTORY
        #     or unitType == UnitTypeId.STARPORT
        # )
        # print("addon place :", addon_place)
        
        location: Point2 = await self.find_placement(unitType, near=position, placement_step=placement_step)
        if (location):
            workers = self.workers.filter(
                lambda worker: self.scv_build_progress(worker) >= 0.9
            )
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

    def constructible(self, position: Point2):
        structures: Units = self.structures
        for structure in structures:
            if (position == structure.position):
                return False
        return (
            self.in_map_bounds(position)
            and self.in_placement_grid(position)
            and self.in_pathing_grid(position)
        )

    def scv_build_progress(self, scv: Unit):
        if (not scv.is_constructing_scv):
            return 1
        building: Unit = self.structures.closest_to(scv)
        if (building.is_ready):
            return 1
        else:
            return building.build_progress

    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
