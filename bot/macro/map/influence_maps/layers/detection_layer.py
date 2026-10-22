from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI
from sc2.ids.effect_id import EffectId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class DetectionLayer:
    bot: BotAI
    detected: InfluenceMap           # 0/1, detected right now
    soon_detected: InfluenceMap      # 0/1, detected now or by a mobile detector within a few seconds
    SCAN_RADIUS: int = 13
    DETECTION_RADIUS: int = 11
    MOBILE_DETECTOR_MARGIN: int = 4  # ~1s of raven movement

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.detected = InfluenceMap(bot)
        self.soon_detected = InfluenceMap(bot)

    def update(self):
        self.detected.reset()
        self.soon_detected.reset()
        self.compute_scans()
        self.compute_detectors()

    def compute_scans(self):
        for effect in self.bot.state.effects:
            if (effect.id == EffectId.SCANNERSWEEP):
                position: Point2 = effect.positions.pop()
                self.detected.update(position, self.SCAN_RADIUS, 1, density_alpha=0)
                self.soon_detected.update(position, self.SCAN_RADIUS, 1, density_alpha=0)

    def compute_detectors(self):
        for turret in self.bot.structures(UnitTypeId.MISSILETURRET):
            self.detected.update(turret.position, self.DETECTION_RADIUS, 1, density_alpha=0)
            self.soon_detected.update(turret.position, self.DETECTION_RADIUS, 1, density_alpha=0)
        for raven in self.bot.units(UnitTypeId.RAVEN):
            self.detected.update(raven.position, self.DETECTION_RADIUS, 1, density_alpha=0)
            self.soon_detected.update(raven.position, self.DETECTION_RADIUS + self.MOBILE_DETECTOR_MARGIN, 1, density_alpha=0)
