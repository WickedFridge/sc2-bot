import math
from bot.utils.ability_tags import AbilityRepair
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import must_repair, add_ons

class BuildingsHandler:
    bot: BotAI
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    async def repair_buildings(self):
        workers = self.bot.workers + self.bot.units(UnitTypeId.MULE)
        available_workers: Units = workers.collecting
        if (available_workers.amount == 0):
            print("no workers to repair o7")
            return
        burning_buildings = self.bot.structures.ready.filter(
            lambda unit: unit.health_percentage < 0.6 or (unit.type_id == UnitTypeId.BUNKER and unit.health_percentage < 1)
        )
        for burning_building in burning_buildings:
            repairing_workers: Units = workers.filter(
                lambda unit: (
                    unit.orders.__len__()
                    and unit.orders[0].ability.id in AbilityRepair
                    and unit.order_target == burning_building.tag
                )
            )
            if (
                (burning_building.type_id in must_repair and repairing_workers.amount < 8)
                or repairing_workers.amount < 3
            ):
                print("pulling worker to repair", burning_building.name)
                
                available_workers.closest_to(burning_building).repair(burning_building)
    
    async def cancel_buildings(self):
        incomplete_buildings: Units = self.bot.structures.filter(
            lambda structure: (
                structure.build_progress < 1
                and structure.type_id not in add_ons
                and (
                    self.bot.workers.amount == 0
                    or self.bot.workers.closest_to(structure).is_constructing_scv == False
                    or self.bot.workers.closest_distance_to(structure) >= structure.radius * math.sqrt(2)
                )
                and structure.health < 50
            )
        )
        for building in incomplete_buildings:
            building(AbilityId.CANCEL_BUILDINPROGRESS)
    
    async def morph_orbitals(self):
        if (self.bot.orbitalTechAvailable()):
            for cc in self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
                if(self.bot.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)):
                    print("Morph Orbital Command")
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def drop_mules(self):
        # find biggest mineral fields near a full base
        mineral_fields: Units = Units([], self.bot)
        ready_townhalls: Units = self.bot.structures(UnitTypeId.COMMANDCENTER).ready + self.bot.structures(UnitTypeId.ORBITALCOMMAND) 
        for townhall in ready_townhalls :
            mineral_fields += self.bot.mineral_field.closer_than(10, townhall)

        if (mineral_fields.amount == 0):
            return
        enemy_units: Units = self.bot.enemy_units
        safe_mineral_fields: Units = (
            mineral_fields if enemy_units.amount == 0 else
            mineral_fields.filter(lambda unit: self.bot.enemy_units.closest_distance_to(unit) > 15)
        )
        if (safe_mineral_fields.amount == 0):
            return
        richest_mineral_field: Unit = max(safe_mineral_fields, key=lambda x: x.mineral_contents)

        # call down a mule on this guy
        # also bank a scan if we have 3 or more orbitals
        orbital_command_amount: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        # scan_to_bank: int = int(orbital_command_amount / 3)
        scan_to_bank: int = 0
        scan_banked: int = 0
        for orbital_command in self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            if (
                orbital_command.energy >= 100
                or scan_banked >= scan_to_bank
            ):
                orbital_command(AbilityId.CALLDOWNMULE_CALLDOWNMULE, richest_mineral_field)
            else:
                scan_banked += 1

    async def handle_supplies(self):
        supplies_raised: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready
        supplies_lowered: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOTLOWERED)
        minimal_distance: float = 6
        ground_enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.is_flying == False)
        for supply in supplies_raised:
            if (ground_enemy_units.amount == 0 or ground_enemy_units.closest_distance_to(supply) > minimal_distance):
                print("Lower Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        for supply in supplies_lowered:
            if (ground_enemy_units.amount >= 1 and ground_enemy_units.closest_distance_to(supply) <= minimal_distance):
                print("Raise Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_RAISE)

    