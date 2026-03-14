from bot.superbot import Superbot
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import dont_attack, menacing, tower_types, creep

class MicroUnit(CachedClass):
    bot: Superbot

    def __init__(self, bot: Superbot):
        super().__init__(bot)
        self.bot = bot

    def is_valid_enemy(self, unit: Unit) -> bool:
        # if (not unit.can_be_attacked):
        #     return False
        if (unit.type_id in dont_attack):
            return False
        return True

    def is_fighting_unit(self, unit: Unit) -> bool:
        return unit.can_attack or unit.type_id in menacing
    
    def can_threaten_air(self, unit: Unit) -> bool:
        return unit.can_attack_air or unit.type_id in menacing

    def is_tower(self, unit: Unit) -> bool:
        return unit.type_id in tower_types
    
    def is_creep_tumor(self, unit: Unit) -> bool:
        return unit.type_id in creep
    
    @custom_cache_once_per_frame
    def enemy_all(self) -> Units:
        """Everything worth considering: real units, towers, and creep tumors."""
        units = self.bot.enemy_units.filter(self.is_valid_enemy)
        towers = self.bot.enemy_structures.filter(self.is_tower)
        tumors = self.bot.enemy_structures.filter(self.is_creep_tumor)
        return units + towers + tumors

    @custom_cache_once_per_frame
    def enemy_fighting(self) -> Units:
        return self.enemy_all.filter(self.is_fighting_unit)
           
    def enemies_threatening_air_in_range(self, unit: Unit, safety_distance: float = 0) -> Units:
        return self.enemy_all.filter(
            lambda enemy: (
                self.can_threaten_air(enemy) and
                enemy.distance_to(unit) <= unit.radius + enemy.radius + enemy.air_range + safety_distance
            )
        )
    
    def enemies_threatening_ground_in_range(
        self, unit: Unit, safety_distance: float = 0, range_override: float | None = None
    ) -> Units:
        """
        Returns enemy units that can threaten the given unit (ground target logic).
        If range_override is set, only considers enemies within that radius first.
        """
        # Step 1: get globally valid combat enemies
        threats = self.enemy_all.filter(self.is_fighting_unit)

        # Step 2: optional proximity filter
        if (range_override):
            threats = threats.closer_than(range_override, unit)

        # Step 3: threat capability check
        threats = threats.filter(
            lambda enemy: (
                (enemy.can_attack_ground or enemy.type_id in menacing)
                and enemy.distance_to(unit) <= unit.radius + enemy.radius + enemy.ground_range + safety_distance
            )
        )

        return threats
    
    def get_potential_targets(self, unit: Unit) -> Units:
        if (unit is None):
            return Units([], self.bot)
        base_range: float = unit.distance_to_weapon_ready + unit.radius

        return self.enemy_all.filter(
            lambda enemy: enemy.distance_to(unit) <= (
                base_range + enemy.radius + 
                (unit.ground_range if not enemy.is_flying else unit.air_range)
            )
        )
    
    def get_enemy_units_in_range(self, unit: Unit) -> Units:
        if (unit is None):
            return Units([], self.bot)
        
        return self.enemy_all.filter(
            lambda enemy: (
                (unit.can_attack_ground and not enemy.is_flying) or
                (unit.can_attack_air and enemy.is_flying)
            )
            and unit.target_in_range(enemy)
        )
    
    def get_local_enemy_units(self, position: Point2, radius: float = 20, only_menacing: bool = False) -> Units:
        enemies = self.enemy_all
        if (only_menacing):
            enemies = enemies.filter(self.is_fighting_unit)

        return enemies.filter(
            lambda enemy: enemy.distance_to(position) <= radius + enemy.radius
        )

    def get_local_enemy_buildings(self, position: Point2) -> Units:
        buildings = self.bot.enemy_structures.filter(self.is_valid_enemy).closer_than(10, position)
        buildings.sort(key=lambda b: b.health)
        return buildings