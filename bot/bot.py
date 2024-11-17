from typing import FrozenSet
from sc2.bot_ai import BotAI, Race
from sc2.data import Result
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
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
        await self.build_supply()
        await self.morph_orbitals()
        await self.drop_mules()
        await self.build_workers()
        await self.build_barracks()
        await self.train_marine()
        await self.attack()
        await self.expand()
        await self.lower_supplies()

        # if (not int(self.time) % 5 and self.time - int(self.time) <= 0.1):
        #     print("waiting for orbital", self.waitingForOrbital())
        #     for cc in self.townhalls(UnitTypeId.COMMANDCENTER).ready:
        #         print("CC is upgrading : ", cc.is_using_ability(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND))

        pass

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
        depot_placement_positions: FrozenSet[Point2] = self.main_base_ramp.corner_depots
        depots: Units = self.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})

        # Filter locations close to finished supply depots
        if depots:
            depot_placement_positions: Set[Point2] = {
                d
                for d in depot_placement_positions if depots.closest_distance_to(d) > 1
            }
            
        if (
            self.supply_cap < 200
            and self.supply_left < 2 + self.supply_used / 10
            and self.can_afford(UnitTypeId.SUPPLYDEPOT)
            and not self.already_pending(UnitTypeId.SUPPLYDEPOT)
        ) :
            print("Build Supply Depot")
            if (len(depot_placement_positions) > 1) :
                target_depot_location: Point2 = depot_placement_positions.pop()
                await self.build(UnitTypeId.SUPPLYDEPOT, target_depot_location)
            else:
                await self.build_custom(UnitTypeId.SUPPLYDEPOT)
    
    async def lower_supplies(self):
        supplies: Units = self.structures(UnitTypeId.SUPPLYDEPOT).ready
        for supply in supplies :
            print("Lower Supply Depot")
            supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

    async def build_barracks(self):
        barracks_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.BARRACKS)
        barracksPosition: Point2 = self.main_base_ramp.barracks_correct_placement
        if (
            barracks_tech_requirement == 1
            and self.can_afford(UnitTypeId.BARRACKS)
            and self.already_pending(UnitTypeId.BARRACKS) < self.townhalls.amount
            and self.units(UnitTypeId.BARRACKS).amount <= 3 * self.townhalls.amount
            and not self.waitingForOrbital()
        ) :
            print("Build Barracks")
            await self.build(UnitTypeId.BARRACKS, barracksPosition)
            # await self.build_custom(unitType=UnitTypeId.BARRACKS, placement_step=5)

    async def train_marine(self):
        barracks: Units = self.structures(UnitTypeId.BARRACKS).ready
        for barrack in barracks :
            if (
                self.can_afford(UnitTypeId.MARINE)
                and barrack.is_idle
                and not self.waitingForOrbital()
            ):
                print("Train Marine")
                barrack.train(UnitTypeId.MARINE)

    async def attack(self):
        army: Units = self.units(UnitTypeId.MARINE).ready
        if (army.amount > 10) :
            for marine in army:
                enemies: Units = self.enemy_units | self.enemy_structures
                enemy_ground_units: Units = enemies.filter(
                    lambda unit: unit.distance_to(marine) < 15 and not unit.is_structure
                )
                enemy_ground_buildings: Units = enemies.filter(
                    lambda unit: unit.distance_to(marine) < 15 and unit.is_structure
                )
                if (enemy_ground_units) :
                    marine.attack(enemy_ground_units.closest_to(marine))
                elif (enemy_ground_buildings) :
                    marine.attack(enemy_ground_buildings.closest_to(marine))
                else :
                    marine.attack(self.enemy_start_locations[0])
        else:
            for marine in army:
                marine.move(self.townhalls.closest_to(self.enemy_start_locations[0]))   

    async def expand(self):
        if (
            self.can_afford(UnitTypeId.COMMANDCENTER)
            and self.townhalls.amount < 3                   
        ):
            print("Expand")
            await self.expand_now()

    async def morph_orbitals(self):
        if (self.orbitalTechAvailable()):
            for cc in self.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
                if(self.can_afford(UnitTypeId.ORBITALCOMMAND)):
                    print("Morph Orbital Command")
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def drop_mules(self):
        for oc in self.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mfs: Units = self.mineral_field.closer_than(10, oc)
            if mfs:
                mf: Unit = max(mfs, key=lambda x: x.mineral_contents)
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

    def orbitalTechAvailable(self):
        return self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) == 1

    def waitingForOrbital(self):
        ccs: Units = self.townhalls(UnitTypeId.COMMANDCENTER).ready.filter(
            lambda cc: cc.is_using_ability(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND) == False
        )
        return self.orbitalTechAvailable() and ccs.amount >= 1

    async def build_custom(self, unitType: UnitTypeId, placement_step=3):
        cc: Unit = self.townhalls.ready.random.position
        workers: Units = self.workers.gathering
        if workers:
            worker: Unit = workers.furthest_to(workers.center)
            location: Point2 = await self.find_placement(unitType, worker.position, placement_step)
            # If a placement location was found
            if location:
                # Order worker to build exactly on that location
                worker.build(unitType, location)

    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
