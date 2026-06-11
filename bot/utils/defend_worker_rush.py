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

Mineral anchor selection:
  - d1: line through c1 (centre of our pulled workers) and c2 (centre of enemy workers).
  - d2: perpendicular bisector of [c1, c2] — splits the map into our side and theirs.
  - safe_mineral:      on c1's side of d2, closest to d1 (good retreat point).
  - offensive_mineral: on c2's side of d2, closest to d1 (good advance/side-step point).
"""

from typing import List, Optional, Tuple

from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

worker_pulled: List[int] = []

def _get_mineral_anchors(
    all_minerals: Units,
    c1: Point2,
    c2: Point2,
) -> Tuple[Optional[Unit], Optional[Unit]]:
    """
    Returns (safe_mineral, offensive_mineral).

    d1: line through c1 and c2.
    d2: perpendicular bisector of [c1, c2] — separates c1's side from c2's side.
      Side is determined by the sign of dot((p - midpoint), (c2 - c1)).

    safe_mineral:      closest to d1 among minerals on c1's side of d2.
    offensive_mineral: closest to d1 among minerals on c2's side of d2.

    Distance to d1 uses the 2D cross-product magnitude, proportional to the true
    distance (the constant |c1-c2| denominator cancels out when comparing).
    """
    midpoint_x: float = (c1.x + c2.x) / 2
    midpoint_y: float = (c1.y + c2.y) / 2
    direction_x: float = c2.x - c1.x
    direction_y: float = c2.y - c1.y

    safe_mineral: Optional[Unit] = None
    offensive_mineral: Optional[Unit] = None
    safe_mineral_dist_to_d1: float = float("inf")
    offensive_mineral_dist_to_d1: float = float("inf")

    for mineral in all_minerals:
        mineral_x: float = mineral.position.x
        mineral_y: float = mineral.position.y
        # side > 0 → c2's side (offensive); side ≤ 0 → c1's side (safe)
        side: float = (mineral_x - midpoint_x) * direction_x + (mineral_y - midpoint_y) * direction_y
        # proportional distance to d1 via 2D cross product
        dist_to_d1: float = abs((mineral_x - c1.x) * direction_y - (mineral_y - c1.y) * direction_x)

        if (side <= 0):
            if (dist_to_d1 < safe_mineral_dist_to_d1):
                safe_mineral_dist_to_d1 = dist_to_d1
                safe_mineral = mineral
        else:
            if (dist_to_d1 < offensive_mineral_dist_to_d1):
                offensive_mineral_dist_to_d1 = dist_to_d1
                offensive_mineral = mineral

    return safe_mineral, offensive_mineral

def choose_workers_to_pull(bot: BotAI, enemy_units: Units, workers_pulled_amount: int) -> Units:
    return bot.workers.filter(
        lambda worker: worker.is_constructing_scv == False
    ).sorted(
        lambda worker: (-worker.health, worker.distance_to_squared(enemy_units.center))
    ).take(workers_pulled_amount)

def wall_is_up(bot: BotAI) -> bool:
    supply_depots: Units = bot.structures(UnitTypeId.SUPPLYDEPOT)
    barracks: Units = bot.structures(UnitTypeId.BARRACKS)

    corner_positions: List[Point2] = list(bot.main_base_ramp.corner_depots)
    depots_at_wall: Units = supply_depots.filter(
        lambda depot: any(depot.position == pos for pos in corner_positions)
    )
    if (depots_at_wall.amount < 2 or barracks.amount < 1):
        return False
    
    barracks_wall: Unit = barracks.closest_to(bot.main_base_ramp.top_center)
    
    if (bot.main_base_ramp.barracks_can_fit_addon):
        return barracks_wall.position == bot.main_base_ramp.barracks_in_middle
    
    if (barracks_wall.position != bot.main_base_ramp.barracks_correct_placement):
        return False
    
    return barracks_wall.has_add_on

def defend_worker_rush(bot: BotAI) -> None:
    if (not bot.workers or not bot.enemy_units):
        return

    if (wall_is_up(bot)):
        return

    if (not bot.mineral_field):
        return

    main_position: Point2 = bot.start_location

    enemy_units: Units = bot.enemy_units.sorted(
        lambda unit: (unit.health + unit.shield, unit.distance_to(main_position))
    )
    best_potential_targets: Units = enemy_units.take(3)

    workers_pulled_amount: int = enemy_units.amount + 1

    # clean worker_pulled of workers that are dead
    for worker_tag in worker_pulled:
        if (not bot.workers.find_by_tag(worker_tag)):
            worker_pulled.remove(worker_tag)

    # filter workers to pull and pull back based on the current pull list
    workers_to_pull: Units = bot.workers.filter(lambda worker: worker.tag in worker_pulled)
    workers_to_pullback: Units = bot.workers.filter(lambda worker: worker.tag not in worker_pulled)

    # if no workers are pulled yet, create the pull
    if (len(worker_pulled) == 0):
        workers_to_pull = choose_workers_to_pull(bot, enemy_units, workers_pulled_amount)
        for worker in workers_to_pull:
            worker_pulled.append(worker.tag)
    # else update the amount of workers pulled if needed
    elif (len(worker_pulled) != workers_pulled_amount):
            workers_to_pull = choose_workers_to_pull(bot, enemy_units, workers_pulled_amount)
            workers_to_pullback = bot.workers.filter(lambda worker: worker.tag not in workers_to_pull.tags)

    c1: Point2 = workers_to_pull.center if workers_to_pull else bot.workers.center
    c2: Point2 = enemy_units.center

    safe_mineral: Optional[Unit]
    offensive_mineral: Optional[Unit]
    safe_mineral, offensive_mineral = _get_mineral_anchors(bot.mineral_field, c1, c2)
    if (not safe_mineral or not offensive_mineral):
        return

    main_minerals: Units = bot.mineral_field.closer_than(12, main_position)
    if (not main_minerals):
        return
    mineral_field_main: Unit = main_minerals.closest_to(bot.enemy_start_locations[0])

    for worker in workers_to_pull:
        enemies_in_range: Units = bot.enemy_units.in_attack_range_of(worker).sorted(lambda unit: (unit.health + unit.shield))
        best_target: Unit = (
            enemies_in_range.first if enemies_in_range else
            best_potential_targets.closest_to(worker)
        )

        if (worker.weapon_cooldown < 6):
            distance: float = worker.distance_to(best_target)

            if (worker.target_in_range(best_target)):
                worker.attack(best_target)
            elif (distance > 3):
                worker.move(best_target.position.towards(worker, -1))
            else:
                worker.gather(offensive_mineral)
        else:
            # On cooldown: gather to keep mining and avoid eating free hits
            worker.gather(safe_mineral)

    for worker in workers_to_pullback:
        if (worker.distance_to(main_position) > 5 and worker.distance_to(mineral_field_main) > 5):
            if (worker.is_carrying_resource):
                worker.return_resource()
            else:
                worker.gather(mineral_field_main)
