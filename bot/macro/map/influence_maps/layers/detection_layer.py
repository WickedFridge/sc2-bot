from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class DetectionLayer:
    bot: BotAI
    detected: InfluenceMap
    SCAN_RADIUS: int = 13
    DETECTION_RADIUS: int = 11

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.detected = InfluenceMap(bot)

    def update(self):
        self.detected.reset()
        self.compute_scans()
        self.compute_detectors()

    def compute_scans(self):
        for effect in self.bot.state.effects:
            if (effect.id == EffectId.SCANNERSWEEP):
                position: Point2 = effect.positions.pop()
                self.detected.update(position, self.SCAN_RADIUS, 1, density_alpha=0)
    
    def compute_detectors(self):
        detectors: Units = self.bot.units(UnitTypeId.RAVEN) + self.bot.structures(UnitTypeId.MISSILETURRET)
        for detector in detectors:
            self.detected.update(detector.position, self.DETECTION_RADIUS, 1, density_alpha=0)
