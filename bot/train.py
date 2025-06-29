from typing import Dict
from bot.combat.combat import Combat
from bot.macro.expansion_manager import Expansions
from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.utils.matchup import Matchup
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Train:
    bot: Superbot
    combat: Combat
    
    def __init__(self, bot: Superbot, combat: Combat) -> None:
        self.bot = bot
        self.combat = combat
    
    async def workers(self, resources: Resources):
        if (self.bot.supply_used >= self.bot.supply_cap):
            return resources
        workers_pending: float = self.bot.already_pending(UnitTypeId.SCV)
        worker_count: float = self.bot.supply_workers + workers_pending
        orbital_count: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        worker_max: int = min([84, 100 - 4 * orbital_count, self.bot.expansions.amount_taken * 22])
        townhalls_type: UnitTypeId = UnitTypeId.ORBITALCOMMAND if self.bot.orbitalTechAvailable() else UnitTypeId.COMMANDCENTER
        townhalls: Units = self.bot.townhalls(townhalls_type).ready.filter(
            lambda unit: (
                unit.is_idle
                or (
                    unit.orders.__len__() == 1
                    and unit.orders[0].ability.id == AbilityId.COMMANDCENTERTRAIN_SCV
                    and unit.orders[0].progress >= 0.95
                )
            )
        )
        
        resources_updated: Resources = resources
        for th in townhalls:
            if (worker_count >= worker_max) :
                return resources_updated
            training_cost: Cost = self.bot.calculate_cost(UnitTypeId.SCV)
            can_build: bool
            resources_updated: Resources
            can_build, resources_updated = resources.update(training_cost)
            if (can_build == False):
                return resources_updated            
            worker_count += 1
            print(f'Train SCV [{worker_count}/{worker_max}]')
            th.train(UnitTypeId.SCV)
        return resources_updated

    async def medivac(self, resources: Resources):
        if (self.bot.supply_used >= self.bot.supply_cap):
            return resources
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready
        max_medivac_amount: int = 12
        medivac_amount: int = self.bot.units(UnitTypeId.MEDIVAC).amount
        bio_amount: int = self.bot.units(UnitTypeId.MARINE).amount + self.bot.units(UnitTypeId.MARAUDER).amount
        barracks_inactive: Units = self.bot.structures(UnitTypeId.BARRACKS).ready.filter(lambda rax: not rax.is_active)
        resources_updated: Resources = resources
        for starport in starports :
            if (
                medivac_amount >= max_medivac_amount
                or (
                    starport.is_active
                    and (
                        not starport.has_reactor
                        or len(starport.orders) == 2
                    )
                )
                or (
                    bio_amount < 10
                    and barracks_inactive.amount > 0
                )
            ):
                return resources_updated

            training_cost: Cost = self.bot.calculate_cost(UnitTypeId.MEDIVAC)
            can_build: bool
            resources_updated: Resources
            can_build, resources_updated = resources.update(training_cost)
            if (can_build == False):
                return resources_updated
            print("Train Medivac")
            starport.train(UnitTypeId.MEDIVAC)
        return resources_updated

    @property
    def should_train_marauders(self):
        marine_count: int = self.bot.units(UnitTypeId.MARINE).amount + self.bot.already_pending(UnitTypeId.MARINE)
        
        default_marauder_ratio: Dict[Matchup, float] = {
            Matchup.TvT: 0,
            Matchup.TvZ: 0.1,
            Matchup.TvP: 0.3,
            Matchup.TvR: 0.2, # TODO fix this
        }
        enemy_armored_ratio: float = (
            0 if self.combat.known_enemy_army.supply == 0
            else self.combat.known_enemy_army.armored_ground_supply / self.combat.known_enemy_army.supply
        )
        armored_ratio: float = (
            0 if self.combat.army_supply == 0
            else self.combat.armored_supply / self.combat.army_supply
        )
        if (
            armored_ratio < enemy_armored_ratio or
            (armored_ratio < default_marauder_ratio[self.bot.matchup] and marine_count >= 8)
        ):
            return True
        return False
    
    async def infantry(self, resources: Resources):
        if (self.bot.supply_used >= self.bot.supply_cap):
            return resources
        barracks_ready: Units = self.bot.structures(UnitTypeId.BARRACKS).ready.filter(
            lambda rax: rax.is_idle or (rax.has_reactor and rax.orders.__len__() < 2)
        )
        resources_updated: Resources = resources
        
        barracks_with_techlabs: Units = barracks_ready.filter(lambda unit: unit.has_techlab)
        other_barracks: Units = barracks_ready.filter(lambda unit: not unit.has_techlab)

        # start with barracks with techlabs
        for barrack in barracks_with_techlabs :
            # if we have a techlab and should train mauraders, train them
            if (self.should_train_marauders):
                training_cost: Cost = self.bot.calculate_cost(UnitTypeId.MARAUDER)
                can_build: bool
                resources_updated: Resources
                can_build, resources_updated = resources.update(training_cost)
                if (can_build == False):
                    continue  # Skip to the next Barracks if we can't afford it

                print("Train Marauder")
                barrack.train(UnitTypeId.MARAUDER)
            # otherwise train marine
            else:                
                training_cost: Cost = self.bot.calculate_cost(UnitTypeId.MARINE)
                can_build: bool
                resources_updated: Resources
                can_build, resources_updated = resources.update(training_cost)
                if (can_build == False):
                    return resources_updated  # Skip if we can't afford it

                print("Train Marine")
                barrack.train(UnitTypeId.MARINE)
        
        # then do other barracks
        for barrack in other_barracks:
            training_cost: Cost = self.bot.calculate_cost(UnitTypeId.MARINE)
            can_build: bool
            resources_updated: Resources
            can_build, resources_updated = resources.update(training_cost)
            if (can_build == False):
                return resources_updated  # Skip if we can't afford it

            print("Train Marine")
            barrack.train(UnitTypeId.MARINE)
        return resources_updated