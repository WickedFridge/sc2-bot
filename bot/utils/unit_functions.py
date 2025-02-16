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