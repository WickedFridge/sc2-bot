"""
defend_worker_rush — micro kiting logic for defending a worker rush in StarCraft II.

Compatible with the base python-sc2 library (https://github.com/BurnySc2/python-sc2).

Usage: call `defend_worker_rush(self)` inside your BotAI `on_step` when you detect a
worker rush (e.g. when enemy workers are in your main base).

The algorithm:
  - Prioritises the 3 lowest-health enemy units as targets.
  - Workers on cooldown gather to a safe mineral patch to keep mining and reset animation.
  - Workers off cooldown attack if in range, advance if far, or side-step to a mineral patch
    to stack up.
"""

from sc2.bot_ai import BotAI
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


def defend_worker_rush(bot: BotAI) -> None:
    if (not bot.workers or not bot.enemy_units):
        return

    main_position: Point2 = bot.start_location
    enemy_main_position: Point2 = bot.enemy_start_locations[0]

    main_minerals: Units = bot.mineral_field.closer_than(12, main_position)
    enemy_minerals: Units = bot.mineral_field.closer_than(12, enemy_main_position)
    if (not main_minerals or not enemy_minerals):
        return

    # Mineral at main closest to the enemy base — used as a safe kiting gather point
    mineral_field_main: Unit = main_minerals.closest_to(enemy_main_position)
    # Mineral at enemy main closest to our base — used to kite enemy workers away
    mineral_field_enemy: Unit = enemy_minerals.closest_to(main_position)

    enemy_units: Units = bot.enemy_units.sorted(
        lambda unit: (unit.health + unit.shield, unit.distance_to(main_position))
    )
    best_potential_targets: Units = enemy_units.take(3)

    for worker in bot.workers:
        enemies_in_range: Units = bot.enemy_units.in_attack_range_of(worker).sorted(lambda unit: (unit.health + unit.shield))
        best_target: Unit = (
            enemies_in_range.first if enemies_in_range else
            best_potential_targets.closest_to(worker)
        )

        if worker.weapon_cooldown < 6:
            distance: float = worker.distance_to(best_target)

            if worker.target_in_range(best_target):
                worker.attack(best_target)
            elif distance > 3:
                worker.move(best_target.position.towards(worker, -1))
            else:
                # Side-step to a mineral patch to reset weapon animation safely
                if worker.distance_to(mineral_field_enemy) > best_target.distance_to(mineral_field_enemy):
                    worker.gather(mineral_field_enemy)
                elif worker.distance_to(mineral_field_main) > best_target.distance_to(mineral_field_main):
                    worker.gather(mineral_field_main)
                else:
                    worker.move(worker.position.towards(best_target, -1))
        else:
            # On cooldown: gather to keep mining and avoid eating free hits
            worker.gather(mineral_field_main)
