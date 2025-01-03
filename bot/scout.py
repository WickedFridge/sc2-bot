from sc2.bot_ai import BotAI


class Scout:
    bot: BotAI
    

    def __init__(self, bot) -> None:
        self.bot = bot
