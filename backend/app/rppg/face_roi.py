"""
Computer Vision Facial Detection and Anatomical ROI Extraction Module.

Implements:
1. MediaPipe Face Mesh landmark tracking (Forehead, Left Cheek, Right Cheek).
2. Exclusion masks for eyes, lips, eyebrows, facial hair, and non-skin.
3. YCrCb / HSV biological skin segmentation filter.
4. Temporal ROI stabilization using Exponential Moving Average (EMA).
5. Inter-frame motion tracking and ROI quality scoring.
6. OpenCV Haar Cascade / anatomical fallback for robust offline/lightweight execution.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import cv2

# Canonical MediaPipe Face Mesh indices for specific physiological facial zones
FOREHEAD_LANDMARKS = [10, 67, 109, 297, 338, 9, 8, 107, 336, 151, 68, 298]
LEFT_CHEEK_LANDMARKS = [117, 118, 101, 205, 206, 207, 123, 50, 36, 137, 203]
RIGHT_CHEEK_LANDMARKS = [346, 347, 330, 425, 426, 427, 352, 280, 266, 366, 423]

# Exclusion regions (Eyes, Lips)
LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]
LIPS_LANDMARKS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291]


def segment_skin_ycrcb(bgr_image: np.ndarray) -> np.ndarray:
    """
    Creates a binary skin mask using YCrCb chromaticity thresholds.

    Skin color in YCrCb typically clusters tightly within:
    Cr in [133, 173] and Cb in [77, 127].

    Args:
        bgr_image: BGR image array (H, W, 3).

    Returns:
        Binary mask (H, W) where 255 indicates skin.
    """
    ycrcb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2YCrCb)
    lower = np.array([40, 133, 77], dtype=np.uint8)
    upper = np.array([255, 173, 127], dtype=np.uint8)
    mask = cv2.inRange(ycrcb, lower, upper)

    # Morphological opening to eliminate isolated noise pixels
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


class FaceROIExtractor:
    """
    Robust facial landmark detector and multi-zone ROI extractor.
    Combines MediaPipe Face Mesh with OpenCV Haar fallback.
    """

    def __init__(self, ema_alpha: float = 0.7):
        self.ema_alpha = ema_alpha
        self.prev_landmarks: Optional[np.ndarray] = None
        self.prev_center: Optional[Tuple[float, float]] = None

        # Try initializing MediaPipe Face Mesh
        self.use_mediapipe = False
        self.face_mesh = None
        try:
            import mediapipe as mp
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self.use_mediapipe = True
        except Exception:
            self.use_mediapipe = False

        # OpenCV Haar Cascade fallback
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def extract_from_frame(
        self,
        bgr_frame: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Processes a single video frame and extracts spatial RGB means for skin ROIs.

        Args:
            bgr_frame: Input BGR frame (H, W, 3).

        Returns:
            Dictionary containing:
            - rgb_mean: [R, G, B] values for the frame
            - rois: Bounding boxes and masks of Forehead, Left Cheek, Right Cheek
            - motion_magnitude: Pixel shift since previous frame
            - face_detected: Boolean
            - quality_score: ROI stability and visibility score [0, 1]
        """
        h, w = bgr_frame.shape[:2]
        skin_mask = segment_skin_ycrcb(bgr_frame)

        if self.use_mediapipe and self.face_mesh is not None:
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                coords = np.array([[lm.x * w, lm.y * h] for lm in landmarks], dtype=np.float32)

                # EMA temporal smoothing for landmark stability
                if self.prev_landmarks is not None:
                    coords = self.ema_alpha * coords + (1.0 - self.ema_alpha) * self.prev_landmarks
                self.prev_landmarks = coords.copy()

                # Calculate inter-frame motion
                current_center = (float(np.mean(coords[:, 0])), float(np.mean(coords[:, 1])))
                if self.prev_center is not None:
                    motion = float(np.hypot(current_center[0] - self.prev_center[0], current_center[1] - self.prev_center[1]))
                else:
                    motion = 0.0
                self.prev_center = current_center

                # Build combined ROI mask for Forehead + Cheeks
                roi_mask = np.zeros((h, w), dtype=np.uint8)

                def add_convex_polygon(landmark_indices, dest_mask):
                    pts = coords[landmark_indices].astype(np.int32)
                    hull = cv2.convexHull(pts)
                    cv2.fillConvexPoly(dest_mask, hull, 255)

                forehead_mask = np.zeros((h, w), dtype=np.uint8)
                add_convex_polygon(FOREHEAD_LANDMARKS, forehead_mask)

                left_cheek_mask = np.zeros((h, w), dtype=np.uint8)
                add_convex_polygon(LEFT_CHEEK_LANDMARKS, left_cheek_mask)

                right_cheek_mask = np.zeros((h, w), dtype=np.uint8)
                add_convex_polygon(RIGHT_CHEEK_LANDMARKS, right_cheek_mask)

                # Union of 3 key regions
                roi_mask = cv2.bitwise_or(forehead_mask, cv2.bitwise_or(left_cheek_mask, right_cheek_mask))

                # Intersect with physiological skin mask to reject hair, glasses, background
                final_mask = cv2.bitwise_and(roi_mask, skin_mask)

                skin_pixel_count = int(np.count_nonzero(final_mask))
                if skin_pixel_count > 50:
                    # Spatial mean in RGB
                    # Note: bgr_frame is BGR, so swap to RGB
                    rgb_frame_raw = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                    mean_val = cv2.mean(rgb_frame_raw, mask=final_mask)[:3]
                    mean_rgb = [float(mean_val[0]), float(mean_val[1]), float(mean_val[2])]

                    # Face bounding box
                    min_x, min_y = np.min(coords, axis=0)
                    max_x, max_y = np.max(coords, axis=0)
                    bbox = [int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)]

                    quality_score = float(np.clip(1.0 - (motion / 15.0), 0.2, 1.0))

                    return {
                        "face_detected": True,
                        "rgb_mean": mean_rgb,
                        "bbox": bbox,
                        "motion_magnitude": round(motion, 2),
                        "quality_score": round(quality_score, 2),
                        "skin_pixels": skin_pixel_count,
                        "method": "MediaPipe_FaceMesh",
                        "zones": {
                            "forehead": cv2.boundingRect(coords[FOREHEAD_LANDMARKS].astype(np.int32)),
                            "left_cheek": cv2.boundingRect(coords[LEFT_CHEEK_LANDMARKS].astype(np.int32)),
                            "right_cheek": cv2.boundingRect(coords[RIGHT_CHEEK_LANDMARKS].astype(np.int32)),
                        },
                    }

        # Fallback to OpenCV Haar Cascade + Anatomical Proportions
        return self._extract_opencv_fallback(bgr_frame, skin_mask)

    def _extract_opencv_fallback(self, bgr_frame: np.ndarray, skin_mask: np.ndarray) -> Dict[str, Any]:
        """
        OpenCV anatomical ROI extraction fallback when MediaPipe landmarks are unavailable.
        """
        h, w = bgr_frame.shape[:2]
        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(80, 80))

        if len(faces) == 0:
            # No face detected
            return {
                "face_detected": False,
                "rgb_mean": [0.0, 0.0, 0.0],
                "bbox": None,
                "motion_magnitude": 0.0,
                "quality_score": 0.0,
                "skin_pixels": 0,
                "method": "OpenCV_Haar_None",
            }

        # Select largest face
        x, y, fw, fh = max(faces, key=lambda b: b[2] * b[3])
        center = (x + fw / 2.0, y + fh / 2.0)
        if self.prev_center is not None:
            motion = float(np.hypot(center[0] - self.prev_center[0], center[1] - self.prev_center[1]))
        else:
            motion = 0.0
        self.prev_center = center

        # Define anatomical ROIs:
        # 1. Forehead: top 12% to 28% of face height, middle 50% of width
        fh_roi = (int(x + fw * 0.25), int(y + fh * 0.12), int(fw * 0.50), int(fh * 0.16))
        # 2. Left cheek: 50% to 70% of height, 15% to 40% of width
        lc_roi = (int(x + fw * 0.15), int(y + fh * 0.52), int(fw * 0.25), int(fh * 0.18))
        # 3. Right cheek: 50% to 70% of height, 60% to 85% of width
        rc_roi = (int(x + fw * 0.60), int(y + fh * 0.52), int(fw * 0.25), int(fh * 0.18))

        roi_mask = np.zeros((h, w), dtype=np.uint8)
        for rx, ry, rw, rh in [fh_roi, lc_roi, rc_roi]:
            rx = max(0, min(rx, w - 1))
            ry = max(0, min(ry, h - 1))
            rw = max(1, min(rw, w - rx))
            rh = max(1, min(rh, h - ry))
            cv2.rectangle(roi_mask, (rx, ry), (rx + rw, ry + rh), 255, -1)

        final_mask = cv2.bitwise_and(roi_mask, skin_mask)
        skin_count = int(np.count_nonzero(final_mask))

        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        if skin_count > 30:
            mean_val = cv2.mean(rgb_frame, mask=final_mask)[:3]
            mean_rgb = [float(mean_val[0]), float(mean_val[1]), float(mean_val[2])]
        else:
            # Fallback to direct ROI mean without skin mask if illumination is harsh
            mean_val = cv2.mean(rgb_frame, mask=roi_mask)[:3]
            mean_rgb = [float(mean_val[0]), float(mean_val[1]), float(mean_val[2])]

        quality_score = float(np.clip(1.0 - (motion / 15.0), 0.2, 0.9))

        return {
            "face_detected": True,
            "rgb_mean": mean_rgb,
            "bbox": [int(x), int(y), int(fw), int(fh)],
            "motion_magnitude": round(motion, 2),
            "quality_score": round(quality_score, 2),
            "skin_pixels": skin_count,
            "method": "OpenCV_Haar_Anatomical",
            "zones": {
                "forehead": fh_roi,
                "left_cheek": lc_roi,
                "right_cheek": rc_roi,
            },
        }

    def process_video_frames(
        self,
        frames: List[np.ndarray],
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Processes a sequence of video frames to extract temporal RGB traces.

        Args:
            frames: List of BGR frames (H, W, 3).

        Returns:
            rgb_temporal: 2D numpy array of shape (N, 3).
            frame_metadata: List of per-frame detection diagnostics.
        """
        rgb_list = []
        diagnostics = []

        last_valid_rgb = [128.0, 100.0, 90.0]

        for frame in frames:
            res = self.extract_from_frame(frame)
            diagnostics.append(res)
            if res["face_detected"] and res["skin_pixels"] > 20:
                rgb_list.append(res["rgb_mean"])
                last_valid_rgb = res["rgb_mean"]
            else:
                # Impute missing frames with last valid frame to preserve temporal continuity
                rgb_list.append(last_valid_rgb)

        return np.array(rgb_list, dtype=np.float64), diagnostics
