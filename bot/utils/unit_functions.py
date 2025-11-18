from sc2.bot_ai import BotAI
from sc2.unit import Unit


def find_by_tag(bot: BotAI, tag: int):
    return (
        bot.units.find_by_tag(tag) or
        bot.enemy_units.find_by_tag(tag) or
        bot.structures.find_by_tag(tag) or
        bot.enemy_structures.find_by_tag(tag) or
        bot.mineral_field.find_by_tag(tag) or
        bot.vespene_geyser.find_by_tag(tag)
    )

def worker_amount_mineral_field(mineral_contents: float) -> float:
    return min(2, 2 * mineral_contents / 500)

def worker_amount_vespene_geyser(gas_contents: float) -> float:
    return min(3, 3 * gas_contents / 250)

def scv_build_progress(bot: BotAI, scv: Unit) -> float:
    if (not scv.is_constructing_scv):
        return 1
    building: Unit = bot.structures.closest_to(scv)
    if (building.distance_to(scv) > building.radius):
        return 0
    return 1 if building.is_ready else building.build_progress