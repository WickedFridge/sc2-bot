from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import hq_types

class BuildingsHandler:
    bot: BotAI
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    async def repair_buildings(self):
        available_workers: Units = self.bot.workers.collecting
        if (available_workers.amount == 0):
            print("no workers to repair o7")
            return
        burning_buildings = self.bot.structures.ready.filter(lambda unit: unit.health_percentage < 0.6)
        for burning_building in burning_buildings:
            repairing_workers: Units = available_workers.filter(
                lambda unit: unit.is_repairing and unit.order_target == burning_building.tag
            )
            if (
                (burning_building.type_id in hq_types and repairing_workers.amount < 8)
                or repairing_workers.amount < 3
            ):
                print("pulling worker to repair", burning_building.name)
                
                self.bot.workers.closest_to(burning_building).repair(burning_building)
    
    async def morph_orbitals(self):
        if (self.bot.orbitalTechAvailable()):
            for cc in self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
                if(self.bot.can_afford(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)):
                    print("Morph Orbital Command")
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def drop_mules(self):
        for orbital_command in self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mineral_fields: Units = self.bot.mineral_field.closer_than(10, orbital_command)
            if mineral_fields:
                mf: Unit = max(mineral_fields, key=lambda x: x.mineral_contents)
                orbital_command(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

    async def handle_supplies(self):
        supplies_raised: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready
        supplies_lowered: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOTLOWERED)
        for supply in supplies_raised:
            if self.bot.enemy_units.amount == 0 or self.bot.enemy_units.closest_distance_to(supply) > 5:
                print("Lower Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        for supply in supplies_lowered:
            if self.bot.enemy_units.amount >= 1 and self.bot.enemy_units.closest_distance_to(supply) <= 5:
                print("Raise Supply Depot")
                supply(AbilityId.MORPH_SUPPLYDEPOT_RAISE)

    