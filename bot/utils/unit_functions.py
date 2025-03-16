from sc2.bot_ai import BotAI


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