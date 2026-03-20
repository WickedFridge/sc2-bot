from typing import override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.utils.army import Army
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import building_priorities, defensive_structures

class MicroBioUnit(MicroUnit):
    stimmable: bool = True
    WITH_MEDIVAC_HEALTH_THRESHOLD: int = 30
    WITHOUT_MEDIVAC_HEALTH_THRESHOLD: int = 45
    RANGE_BUFFER: int = 2
        
    def stim(self, bio_unit: Unit, force: bool = False):
        DANGER_THRESHOLD: float = 5 if not force else 0
        if (
            self.bot.already_pending_upgrade(UpgradeId.STIMPACK) < 1
            or bio_unit.has_buff(BuffId.STIMPACK)
            or bio_unit.has_buff(BuffId.STIMPACKMARAUDER)
            or not self.stimmable
        ):
            return
        
        MEDIVAC_ENERGY_THRESHOLD: int = 25
        MEDIVAC_HEALTH_THRESHOLD: int = 40
        
        local_usable_medivacs: Units = self.bot.units(UnitTypeId.MEDIVAC).filter(
            lambda medivac: (
                medivac.distance_to(bio_unit) <= 10
                and medivac.energy >= MEDIVAC_ENERGY_THRESHOLD
                and medivac.health >= MEDIVAC_HEALTH_THRESHOLD
            )
        )
        targets_in_range: Units = self.get_enemy_units_in_range(bio_unit, include_buildings=True)
        
        if (
            (
                bio_unit.health >= self.WITHOUT_MEDIVAC_HEALTH_THRESHOLD
                or (
                    local_usable_medivacs.amount >= 1
                    and bio_unit.health >= self.WITH_MEDIVAC_HEALTH_THRESHOLD
                )
            )
            and (
                # only stimming if there's enough danger or a target in range
                targets_in_range.amount >= 1
                or self.bot.map.influence_maps.danger.ground[bio_unit.position] >= DANGER_THRESHOLD
            )
        ):
            bio_unit(AbilityId.EFFECT_STIM)
    
    @override
    async def fight_defense(self, bio_unit: Unit, local_units: Units):
        # # defend the closest base under attack if it's not too close to us
        # bases_under_attack: Expansions = self.bot.expansions.taken.under_attack
        # if (bases_under_attack.amount >= 1):
        #     closest_base_under_attack: Expansion = bases_under_attack.closest_to(bio)
        #     if (closest_base_under_attack.position.distance_to(bio) > 10):
        #         bio.attack(closest_base_under_attack.retreat_position)
        #         return
        
        enemy_units: Units = self.enemy_all.sorted(lambda enemy_unit: (enemy_unit.distance_to(bio_unit), enemy_unit.health + enemy_unit.shield))
        if (enemy_units.amount == 0):
            print("[Error] no enemy units to attack")
            await self.fight(bio_unit, local_units)
            return
        
        close_defensive_structure: Units = self.bot.structures(defensive_structures).filter(
            lambda defense: defense.distance_to(bio_unit) <= 10 and defense.build_progress >= 0.9
        )
        closest_defensive_structure: Unit = (
            close_defensive_structure.closest_to(bio_unit)
            if close_defensive_structure
            else None
        )
        if (closest_defensive_structure):
            # handle stim
            self.stim(bio_unit)
            self.fight_around_structure(bio_unit, enemy_units, closest_defensive_structure)
        else:
            await self.fight(bio_unit, local_units)

    @override
    async def fight(self, bio_unit: Unit, local_units: Units, chase: bool = False):
        enemy_units_in_range = self.get_enemy_units_in_range(bio_unit)
        potential_targets: Units = self.get_potential_targets(bio_unit)
        buildings_in_range = self.bot.enemy_structures.filter(
            lambda building: bio_unit.target_in_range(building)
        ).sorted(
            lambda building: (building.type_id not in building_priorities, building.health + building.shield)
        )
        local_medivacs: Units = local_units(UnitTypeId.MEDIVAC)
        loaded_medivacs: Units = local_medivacs.filter(lambda unit: unit.cargo_used > 0)

        # Determine if we should kite back or pressure forward
        # This depends on the enemy range + movement speed
        # If their average range is less than our range, kite back
        # If their average speed is less than our speed, and their range similar, kite back
        # Otherwise, pressure forward
        
        average_ground_range: float = Army(local_units, self.bot).average_ground_range
        shorter_range: bool = any([enemy_unit.ground_range < average_ground_range for enemy_unit in enemy_units_in_range])
        other_enemies: Units = self.enemy_fighting.sorted(
            lambda enemy_unit: (enemy_unit.distance_to(bio_unit), enemy_unit.shield, enemy_unit.health + enemy_unit.shield)
        )

        # First, if we're chasing and only have a building in range, shoot at it
        if (chase and potential_targets.amount == 0 and buildings_in_range.amount >= 1):
            self.stim(bio_unit)
            if (bio_unit.weapon_cooldown <= self.WEAPON_READY_THRESHOLD):
                bio_unit.attack(buildings_in_range.first)
            elif (other_enemies.amount == 0):
                print("Error, no enemy to chase !")
            else:
                target: Unit = other_enemies.first
                best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(bio_unit, target)
                bio_unit.move(best_position)
            return

        if (
            enemy_units_in_range.amount >= 1
            or potential_targets.amount >= 1
        ):
            self.stim(bio_unit)

        # ----- CASE 1: MELEE ENGAGEMENT (kite backward) -----
        if (shorter_range and self.handle_engagement(
            bio_unit,
            enemy_units_in_range,
            other_enemies,
        )):
            return


        # ----- CASE 2: PURE RANGED ENGAGEMENT (pressure forward) -----
        if (self.handle_engagement(
            bio_unit,
            potential_targets,
            other_enemies,
            kite_forward=True
        )):
            return

        # SECONDARY CASE: No targets, but enemy units exist
        if (buildings_in_range.amount >= 1 and bio_unit.weapon_ready):
            self.stim(bio_unit)
            bio_unit.attack(buildings_in_range.first)
            return

        # if everything isn't unloaded, regroup before attacking
        if (loaded_medivacs):
            bio_unit.move(local_units.center)
            return

        self.stim(bio_unit)
        if (other_enemies.amount == 0):
            # No valid targets regroup
            bio_unit.move(local_units.center)
            return
        target: Unit = other_enemies.first
        best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(bio_unit, target)
        bio_unit.move(best_position)

    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        self.stim(unit)
        await super().harass(unit, local_units, workers)
    
    @override
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        target: Unit = enemy_buildings.first
        if (
            unit.health_percentage >= 0.85 and (
                target.health > 100
                or enemy_buildings.amount >= 2
            )
        ):
            self.stim(unit, force=True)
        await super().kill_buildings(unit, local_units, enemy_buildings)
    
    
    @override
    async def disengage(self, bio_unit: Unit, local_units: Units):
        enemy_units_in_range = self.get_enemy_units_in_range(bio_unit)
        
        # handle stim
        self.stim(bio_unit)

        if (enemy_units_in_range.amount >= 1):
            self.hit_n_run(bio_unit, enemy_units_in_range)
        else:
            await self.retreat(bio_unit, local_units)
    