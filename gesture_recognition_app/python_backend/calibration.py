"""
ScreenCalibrator
================
Maps camera image coordinates → screen coordinates using a 2D homography.

Calibration flow:
  1. User identifies where each of the 4 screen corners appears in the
     camera image (by clicking on the live feed).
  2. We compute H = findHomography(src_image_pts, screen_corner_pts).
  3. Every subsequent fingertip position is transformed by H to obtain
     the exact pixel position on the display surface.

This corrects:
  - Resolution mismatches between camera and display
  - Perspective distortion (Kinect mounted at an angle)
  - Offset that grows near the screen edges / at close depth
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Where the calibration file is persisted
_DATA_DIR = Path(__file__).parent.parent.parent / "data"
CALIBRATION_FILE = _DATA_DIR / "screen_calibration.json"

# Corner capture order (must match CalibrationPanel.jsx CORNER_NAMES)
CORNER_ORDER = ["top_left", "top_right", "bottom_right", "bottom_left"]


class ScreenCalibrator:
    """
    Computes and applies a perspective homography that maps camera-image
    coordinates to on-screen pixel coordinates.
    """

    def __init__(self, screen_width: int = 1920, screen_height: int = 1080):
        # screen_width/height are stored for informational purposes only.
        # apply() always outputs NORMALIZED coordinates in [0, 1] × [0, 1]
        # so no screen-size knowledge is needed on the frontend.
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Source points in camera-image space (filled during calibration)
        self.src_pts: List[Tuple[float, float]] = []

        # Computed 3×3 homography matrix (float64)
        self.homography: Optional[np.ndarray] = None
        self.is_calibrated: bool = False

        # Destination corners are always NORMALIZED [0,1].
        # This means apply() returns values in [0,1] × [0,1] regardless
        # of display resolution — the frontend multiplies by 100 to get %.
        self._dst_pts = np.array(
            [
                [0.0, 0.0],   # top-left
                [1.0, 0.0],   # top-right
                [1.0, 1.0],   # bottom-right
                [0.0, 1.0],   # bottom-left
            ],
            dtype=np.float32,
        )

        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Reset in-progress capture (keeps any existing valid homography)."""
        self.src_pts = []
        logger.info("Calibration capture started – waiting for 4 corner points")

    def add_corner(self, x: float, y: float) -> int:
        """
        Record a clicked image coordinate for the current corner.

        Returns
        -------
        int
            Number of corners captured so far (1–4).
        """
        self.src_pts.append((float(x), float(y)))
        idx = len(self.src_pts)
        logger.info(
            "Corner %d/4 captured – image=(%.1f, %.1f)  [%s]",
            idx,
            x,
            y,
            CORNER_ORDER[idx - 1],
        )
        return idx

    @property
    def corners_captured(self) -> int:
        return len(self.src_pts)

    def can_compute(self) -> bool:
        return len(self.src_pts) >= 4

    def compute_homography(self) -> Tuple[bool, str]:
        """
        Compute the homography from the 4 collected corner points.

        Returns
        -------
        (success, message)
        """
        if not self.can_compute():
            return False, f"Need 4 corners, only have {len(self.src_pts)}"

        src = np.array(self.src_pts[:4], dtype=np.float32)
        dst = self._dst_pts.copy()

        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if H is None:
            return False, "findHomography failed – points may be collinear"

        # Sanity-check: average reprojection error should be small
        err = self._reprojection_error(src, dst, H)
        if err > 50:
            logger.warning("High reprojection error: %.1f px – calibration may be inaccurate", err)

        self.homography = H
        self.is_calibrated = True

        msg = f"Homography computed – avg reprojection error: {err:.1f} px"
        logger.info(msg)
        self._save()
        return True, msg

    def apply(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transform a camera-image point to normalized screen coordinates.

        Returns
        -------
        (nx, ny) : floats in [0.0, 1.0] × [0.0, 1.0]
            Ready to use as CSS percentages (multiply by 100).
            Works at any display resolution without any further conversion.

        If calibration is not available returns (None, None).
        """
        if self.homography is None:
            return None, None

        pt = np.array([[[float(x), float(y)]]], dtype=np.float32)
        result = cv2.perspectiveTransform(pt, self.homography)
        nx = float(np.clip(result[0, 0, 0], 0.0, 1.0))
        ny = float(np.clip(result[0, 0, 1], 0.0, 1.0))
        return nx, ny

    def status(self) -> dict:
        return {
            "is_calibrated": self.is_calibrated,
            "corners_captured": self.corners_captured,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
        }

    def reset(self) -> None:
        """Clear all calibration data (in-memory and on disk)."""
        self.src_pts = []
        self.homography = None
        self.is_calibrated = False
        if CALIBRATION_FILE.exists():
            CALIBRATION_FILE.unlink()
        logger.info("Screen calibration reset")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _reprojection_error(src: np.ndarray, dst: np.ndarray, H: np.ndarray) -> float:
        projected = cv2.perspectiveTransform(
            src.reshape(1, -1, 2).astype(np.float32), H
        ).reshape(-1, 2)
        return float(np.mean(np.linalg.norm(projected - dst, axis=1)))

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "src_pts": self.src_pts,
            "homography": self.homography.tolist() if self.homography is not None else None,
            "is_calibrated": self.is_calibrated,
        }
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Screen calibration saved → %s", CALIBRATION_FILE)

    def _load(self) -> None:
        if not CALIBRATION_FILE.exists():
            return
        try:
            with open(CALIBRATION_FILE) as f:
                data = json.load(f)
            self.screen_width = data.get("screen_width", self.screen_width)
            self.screen_height = data.get("screen_height", self.screen_height)
            self.src_pts = [tuple(p) for p in data.get("src_pts", [])]
            raw_H = data.get("homography")
            if raw_H is not None:
                self.homography = np.array(raw_H, dtype=np.float64)
                self.is_calibrated = data.get("is_calibrated", True)
            logger.info(
                "Screen calibration loaded (calibrated=%s)", self.is_calibrated
            )
        except Exception as exc:
            logger.warning("Could not load screen calibration: %s", exc)
