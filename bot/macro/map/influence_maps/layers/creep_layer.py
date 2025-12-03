import numpy as np
from scipy.ndimage import distance_transform_edt, convolve
from scipy.signal import convolve2d

from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.bot_ai import BotAI
from sc2.position import Point2


class CreepLayer:
    creep_map: InfluenceMap              # boolean mask
    creep_assumed: InfluenceMap          # float32, creep assuming unknown tiles are creep too
    distance_to_creep: InfluenceMap      # float32, grid of distances to nearest creep
    edge: InfluenceMap                   # float32, edge of creep
    density: InfluenceMap                # float32, smoothed creep
    tumor_candidates: InfluenceMap       # erosion 10 radius
    bonus: InfluenceMap                  # float32, bonus danger by creep
    grad_x: np.ndarray
    grad_y: np.ndarray
    
    CREEP_BONUS: float = 1.2
    TUMOR_RADIUS: float = 10
    SLOW_UPDATE_INTERVAL: int = 8  # compute heavy maps every N frames
    MIN_CREEP_TILES_FOR_SLOW: int = 150  # skip heavy work if creep very small

    def __init__(self, bot: BotAI):
        self.bot = bot
        self.creep_map: InfluenceMap = InfluenceMap(bot, dtype=np.float32)
        self.creep_assumed: InfluenceMap = InfluenceMap(bot, dtype=np.float32)
        self.distance_to_creep: InfluenceMap = InfluenceMap(bot, dtype=np.float32)
        self.edge: InfluenceMap = InfluenceMap(bot, dtype=np.float32)
        self.density: InfluenceMap = InfluenceMap(bot, dtype=np.float32)
        self.tumor_candidates: InfluenceMap = InfluenceMap(bot, dtype=np.float32)
        self.bonus: InfluenceMap = InfluenceMap(bot, dtype=np.float32)
        
        # Gradient of density map (grad_x, grad_y)
        self.grad_x: np.ndarray = None
        self.grad_y: np.ndarray = None
        
    
    def compute_raw_creep(self):
        raw_creep: np.ndarray = self.bot.state.creep.data_numpy.astype(np.float32)
        self.creep_map.map[:] = raw_creep
    
    def compute_empty_maps(self):
        self.distance_to_creep.map[:] = np.full_like(self.distance_to_creep.map, fill_value=np.inf, dtype=np.float32)
        self.edge.map[:] = 0.0
        self.density.map[:] = 0.0
        self.tumor_candidates.map[:] = 0.0
        self.bonus.map[:] = 0.0
        # self.tumor_density.map[:] = 0.0
        self.grad_x = np.zeros_like(self.density.map)
        self.grad_y = np.zeros_like(self.density.map)
    
    def compute_assumed_creep(self):
        """
        Expand creep into unseen tiles within radius ~5.
        Does NOT touch real creep — stored in self.creep_assumed.
        """
        creep: np.ndarray = self.creep_map.map
        visibility: np.ndarray = self.bot.state.visibility.data_numpy  # 0 = not visible, 1 = fogged, 2 = visible

        # --- 1. build radius-5 disk kernel ---
        R: float = 5
        y, x = np.ogrid[-R:R+1, -R:R+1]
        kernel = (x*x + y*y <= R*R).astype(np.float32)

        # --- 2. convolve to find tiles near real creep ---
        creep_near: np.ndarray = convolve2d(creep, kernel, mode="same", boundary="fill", fillvalue=0)

        # --- 3. mark unseen tiles near creep as creep ---
        assumed: np.ndarray = (creep == 1) | ((visibility < 2) & (creep_near > 0))

        self.creep_assumed.map[:] = assumed.astype(np.float32)
    
    def compute_creep_density(self):
        creep: np.ndarray = self.creep_assumed.map

        # distance to non-creep
        dist_to_noncreep: np.ndarray = distance_transform_edt(creep != 0)

        # Normalize by radius to get values in [0, ~2]
        R = self.TUMOR_RADIUS

        density: np.ndarray = dist_to_noncreep / R   # 0 = border, >=1 inside thick creep
        density = np.clip(density, 0, None).astype(np.float32)
        
        self.density.map[:] = density
    
    def compute_gradients(self):
        self.grad_y, self.grad_x = np.gradient(self.density.map)
    
    def compute_distance_to_creep(self):
        self.distance_to_creep.map[:] = distance_transform_edt(1 - self.creep_map.map)

    def compute_creep_edge(self):
        """Return binary map of tiles on the edge/frontier of creep."""
        # Kernel for neighborhood (3x3)
        kernel: np.ndarray = np.ones((3, 3), dtype=np.float32)
        neighbor_count: np.ndarray = convolve(self.creep_map.map, kernel, mode='constant', cval=0.0)

        # Edge = tile is creep but has at least one neighbor without creep
        edge: np.ndarray = (self.creep_assumed.map == 1) & (neighbor_count < 9)
        self.edge.map[:] = edge.astype(np.float32)
    
    def compute_tumor_candidates(self):
        if (self.bot.state.game_loop % self.SLOW_UPDATE_INTERVAL != 0):
            return
        creep: np.ndarray = self.creep_map.map
        pathing: np.ndarray = self.bot.game_info.pathing_grid.data_numpy
        
        height, width = creep.shape

        ys, xs = np.where(creep)
        ymin = max(0, ys.min())
        ymax = min(height - 1, ys.max())
        xmin = max(0, xs.min())
        xmax = min(width - 1, xs.max())

        # add a margin so tumor detection near edges is correct
        margin = int(self.TUMOR_RADIUS * 1.2) + 2
        cy0 = max(0, ymin - margin)
        cy1 = min(height, ymax + margin + 1)
        cx0 = max(0, xmin - margin)
        cx1 = min(width, xmax + margin + 1)

        # cropped arrays
        creep_sub: np.ndarray = creep[cy0:cy1, cx0:cx1]
        path_sub: np.ndarray = pathing[cy0:cy1, cx0:cx1]

        # -------------------------
        # Fast tumor candidates via EDT (respecting pathing)
        # -------------------------
        # mask of pathable tiles that are NOT creeped (these are blockers)
        noncreep_pathable: np.ndarray = ((creep_sub == 0) & (path_sub == 1)).astype(np.uint8)
        
        # Distance to nearest non-creep tile
        # Tiles that have distance >= R have full creep coverage
        if (noncreep_pathable.any()):
            dist_to_noncreep_pathable: np.ndarray = distance_transform_edt(noncreep_pathable == 0)
        else:
            # no noncreep pathable tiles in crop -> everything creeped or unpathable -> distance large
            dist_to_noncreep_pathable: np.ndarray = np.full_like(creep_sub, fill_value=9999, dtype=np.float32)

        # Build a disk of radius 10
        R = self.TUMOR_RADIUS

        candidate_sub: np.ndarray = ((dist_to_noncreep_pathable >= R) & (path_sub == 1)).astype(np.float32)

        # float32 influence map (1 = candidate, 0 = not)
        # Write candidates into InfluenceMap (only cropped region)
        self.tumor_candidates.map[:] = 0.0
        self.tumor_candidates.map[cy0:cy1, cx0:cx1] = candidate_sub
    
    def compute_bonus(self):
        self.bonus.map[:] = np.where(self.creep_map.map, self.CREEP_BONUS, 1.0).astype(np.float32)

    
    def update(self) -> None:
        self.compute_raw_creep()
        if (not self.creep_map.map.any()):
            self.compute_empty_maps()
            return
        self.compute_assumed_creep()
        self.compute_distance_to_creep()
        self.compute_creep_edge()        
        self.compute_creep_density()
        self.compute_gradients()
        self.compute_tumor_candidates()
        self.compute_bonus()
    
    
    # -----------------------------
    # Queries
    # -----------------------------
    def closest_creep_edge(self, pos: Point2) -> Point2 | None:
        """Return nearest edge tile (creep frontier) to a position."""
        y_idxs, x_idxs = np.where(self.edge.map)
        if len(x_idxs) == 0:
            return None

        dx = x_idxs - pos.x
        dy = y_idxs - pos.y
        dist2 = dx*dx + dy*dy
        idx = np.argmin(dist2)
        return Point2((x_idxs[idx], y_idxs[idx]))

    def direction_to_tumor(self, pos: Point2) -> Point2 | None:
        """Return normalized vector pointing toward nearest tumor based on gradient."""
        y, x = int(pos.y), int(pos.x)
        grad_x = self.grad_x[y, x]
        grad_y = self.grad_y[y, x]
        vec = np.array([grad_x, grad_y], dtype=np.float32)
        length = np.linalg.norm(vec)
        if length < 1e-3:
            # Gradient too small → fallback to nearest edge
            target = self.closest_creep_edge(pos)
            if target is None:
                return None
            vec = np.array([target.x - pos.x, target.y - pos.y], dtype=np.float32)
            length = np.linalg.norm(vec)
            if length < 1e-3:
                return None
        return Point2((pos.x + vec[0]/length, pos.y + vec[1]/length))
    
    # ----------------------------------------------------------
    # Nearest creep tile to a given position
    # ----------------------------------------------------------
    def closest_creep_clamp(self, pos: Point2, threshold: float = 0.5) -> Point2 | None:
        density_map = self.density.map
        h, w = density_map.shape

        ys, xs = np.where(self.density.map >= threshold)
        if (len(xs) == 0):
            return None
        
        # Clamp inside map bounds
        cx = max(0, min(pos.x, w - 1))
        cy = max(0, min(pos.x, h - 1))

        # Compute squared distance to avoid sqrt cost
        dx = xs - cx
        dy = ys - cy
        dist2 = dx*dx + dy*dy

        idx = np.argmin(dist2)

        # 4) Convert tile → world Point2
        return Point2((xs[idx], ys[idx]))
    
    def max_density_in_radius(self, pos: Point2, radius: float) -> tuple[float, Point2 | None]:
        x1, y1, masked = self.density.read_values(pos, radius)
        if (masked.count() == 0):
            return 0.0, None
        
        max_val: float = masked.max()
        if (max_val <= 0):
            return 0.0, None

        # find tile with max density
        ys, xs = np.where(masked == max_val)
        iy = ys[0]
        ix = xs[0]

        return max_val, Point2((x1 + ix, y1 + iy))