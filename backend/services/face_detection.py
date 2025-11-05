"""Face detection service using dlib for fighter image processing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import dlib
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceBox:
    """Represents a detected face bounding box."""

    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0

    @property
    def area(self) -> int:
        """Calculate the area of the bounding box."""
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        """Calculate the center point of the bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)


class FaceDetectionService:
    """Service for detecting faces in fighter images using dlib."""

    def __init__(self):
        """Initialize face detection models."""
        try:
            # Load HOG detector (fast, CPU-friendly)
            self.hog_detector = dlib.get_frontal_face_detector()
            logger.info("HOG face detector loaded successfully")

            # CNN detector will be lazy-loaded if needed
            self.cnn_detector = None
            self._cnn_model_path = None

        except Exception as e:
            logger.error(f"Failed to initialize face detection models: {e}")
            raise

    def _load_cnn_detector(self):
        """Lazy load CNN detector for more accurate detection."""
        if self.cnn_detector is not None:
            return

        try:
            # Try to load CNN model if available
            # Note: This requires downloading the model file separately
            model_path = Path(__file__).parent.parent.parent / "models" / "mmod_human_face_detector.dat"

            if model_path.exists():
                self.cnn_detector = dlib.cnn_face_detection_model_v1(str(model_path))
                self._cnn_model_path = str(model_path)
                logger.info("CNN face detector loaded successfully")
            else:
                logger.warning(
                    f"CNN face detector model not found at {model_path}. "
                    "Only HOG detector will be available."
                )
        except Exception as e:
            logger.warning(f"Failed to load CNN detector: {e}")

    def detect_faces(
        self, image_path: str | Path, use_cnn: bool = False
    ) -> list[FaceBox]:
        """
        Detect all faces in an image.

        Args:
            image_path: Path to the image file
            use_cnn: If True, use CNN detector (slower but more accurate)

        Returns:
            List of detected face bounding boxes

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image cannot be loaded
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Load image
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Failed to load image: {image_path}")

            # Convert BGR to RGB (dlib expects RGB)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        except Exception as e:
            raise ValueError(f"Error loading image {image_path}: {e}")

        # Detect faces
        faces = []

        if use_cnn:
            self._load_cnn_detector()
            if self.cnn_detector is not None:
                faces = self._detect_with_cnn(rgb_image)
            else:
                logger.warning("CNN detector not available, falling back to HOG")
                faces = self._detect_with_hog(rgb_image)
        else:
            faces = self._detect_with_hog(rgb_image)

            # If no faces found with HOG, try CNN as fallback
            if not faces and self._cnn_model_path:
                logger.info("No faces found with HOG, trying CNN detector")
                self._load_cnn_detector()
                if self.cnn_detector is not None:
                    faces = self._detect_with_cnn(rgb_image)

        logger.info(f"Detected {len(faces)} face(s) in {image_path.name}")
        return faces

    def _detect_with_hog(self, image: np.ndarray) -> list[FaceBox]:
        """Detect faces using HOG detector."""
        try:
            # Run detection
            detections = self.hog_detector(image, 1)

            faces = []
            for detection in detections:
                face = FaceBox(
                    x=detection.left(),
                    y=detection.top(),
                    width=detection.width(),
                    height=detection.height(),
                    confidence=1.0,  # HOG doesn't provide confidence scores
                )
                faces.append(face)

            return faces

        except Exception as e:
            logger.error(f"HOG detection failed: {e}")
            return []

    def _detect_with_cnn(self, image: np.ndarray) -> list[FaceBox]:
        """Detect faces using CNN detector."""
        try:
            # Run detection
            detections = self.cnn_detector(image, 1)

            faces = []
            for detection in detections:
                # CNN detector provides confidence scores
                confidence = detection.confidence
                rect = detection.rect

                face = FaceBox(
                    x=rect.left(),
                    y=rect.top(),
                    width=rect.width(),
                    height=rect.height(),
                    confidence=float(confidence),
                )
                faces.append(face)

            return faces

        except Exception as e:
            logger.error(f"CNN detection failed: {e}")
            return []

    def get_primary_face(self, faces: list[FaceBox]) -> FaceBox | None:
        """
        Select the most likely fighter face from multiple detections.

        Strategy:
        1. If only one face, return it
        2. If multiple faces, prefer:
           - Largest face (likely the main subject)
           - Highest confidence (for CNN detections)

        Args:
            faces: List of detected faces

        Returns:
            The primary face, or None if no faces
        """
        if not faces:
            return None

        if len(faces) == 1:
            return faces[0]

        # Multiple faces: select the largest one
        # (assuming the fighter is the main subject)
        primary = max(faces, key=lambda f: f.area)

        if len(faces) > 1:
            logger.warning(
                f"Multiple faces detected ({len(faces)}), selected largest face "
                f"(area={primary.area})"
            )

        return primary

    def calculate_confidence(
        self, face: FaceBox, image: np.ndarray
    ) -> float:
        """
        Estimate detection confidence based on face characteristics.

        Factors considered:
        - Face size relative to image
        - Position in image (centered faces score higher)
        - Aspect ratio (faces should be roughly square-ish)

        Args:
            face: Detected face bounding box
            image: Original image as numpy array

        Returns:
            Confidence score between 0 and 1
        """
        height, width = image.shape[:2]
        image_area = height * width

        # Factor 1: Size relative to image (larger is better, up to a point)
        size_ratio = face.area / image_area
        size_score = min(size_ratio * 10, 1.0)  # Cap at 1.0

        # Factor 2: Position (centered is better)
        face_center_x, face_center_y = face.center
        image_center_x, image_center_y = width // 2, height // 2

        center_dist = np.sqrt(
            (face_center_x - image_center_x) ** 2 +
            (face_center_y - image_center_y) ** 2
        )
        max_dist = np.sqrt(image_center_x ** 2 + image_center_y ** 2)
        position_score = 1.0 - (center_dist / max_dist)

        # Factor 3: Aspect ratio (should be somewhat square)
        aspect_ratio = face.width / face.height if face.height > 0 else 0
        # Ideal is around 0.8-1.2 (slightly taller than wide is normal for faces)
        aspect_score = 1.0 - abs(1.0 - aspect_ratio)
        aspect_score = max(0, min(aspect_score, 1.0))

        # Combine factors (weighted average)
        confidence = (
            0.4 * size_score +
            0.3 * position_score +
            0.3 * aspect_score
        )

        # If the face has its own confidence (from CNN), factor that in
        if face.confidence < 1.0:
            confidence = 0.7 * confidence + 0.3 * face.confidence

        return float(confidence)
