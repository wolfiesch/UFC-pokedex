"""Intelligent image cropping service for fighter portraits."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .face_detection import FaceBox, FaceDetectionService

logger = logging.getLogger(__name__)


@dataclass
class CropBox:
    """Represents a crop box for an image."""

    x: int
    y: int
    width: int
    height: int

    def to_slice(self) -> tuple[slice, slice]:
        """Convert to numpy slices for array indexing."""
        return (
            slice(self.y, self.y + self.height),
            slice(self.x, self.x + self.width),
        )


@dataclass
class CropResult:
    """Result of an image cropping operation."""

    success: bool
    cropped_path: str | None
    confidence: float
    face_area_percent: float  # Face size relative to crop
    quality_score: float  # 0-1, composite quality metric
    fallback_to_original: bool
    error_message: str | None = None


class ImageCropper:
    """Service for intelligently cropping fighter images to focus on faces."""

    # Minimum image dimensions to process
    MIN_IMAGE_WIDTH = 200
    MIN_IMAGE_HEIGHT = 200

    # Target output size (square)
    TARGET_SIZE = (512, 512)

    # Padding ratios relative to face box
    PADDING_TOP = 0.4  # Head room above face
    PADDING_SIDES = 0.3  # Space on left/right
    PADDING_BOTTOM = 0.6  # Include shoulders/upper torso

    # Quality thresholds
    MIN_CONFIDENCE = 0.5  # Minimum confidence to accept crop
    MIN_FACE_PERCENT = 0.35  # Minimum face size in crop
    MAX_FACE_PERCENT = 0.55  # Maximum face size in crop

    def __init__(
        self,
        target_size: tuple[int, int] | None = None,
    ):
        """
        Initialize image cropper.

        Args:
            target_size: Target output size (width, height). Default: (512, 512)
        """
        self.target_size = target_size or self.TARGET_SIZE
        self.face_detector = FaceDetectionService()

    def crop_to_face(
        self,
        image_path: str | Path,
        output_path: str | Path,
    ) -> CropResult:
        """
        Main entry point - detect face and create intelligent crop.

        This is a non-destructive operation. The original image is never modified.

        Args:
            image_path: Path to the original image
            output_path: Path to save the cropped image

        Returns:
            CropResult with success status and metadata
        """
        image_path = Path(image_path)
        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                return CropResult(
                    success=False,
                    cropped_path=None,
                    confidence=0.0,
                    face_area_percent=0.0,
                    quality_score=0.0,
                    fallback_to_original=True,
                    error_message=f"Failed to load image: {image_path}",
                )

            height, width = image.shape[:2]

            # Check minimum dimensions
            if width < self.MIN_IMAGE_WIDTH or height < self.MIN_IMAGE_HEIGHT:
                logger.warning(
                    f"Image too small ({width}x{height}), skipping crop: {image_path.name}"
                )
                return CropResult(
                    success=False,
                    cropped_path=None,
                    confidence=0.0,
                    face_area_percent=0.0,
                    quality_score=0.0,
                    fallback_to_original=True,
                    error_message=f"Image too small: {width}x{height}",
                )

            # Detect faces
            faces = self.face_detector.detect_faces(image_path)

            if not faces:
                logger.info(f"No faces detected in {image_path.name}, skipping crop")
                return CropResult(
                    success=False,
                    cropped_path=None,
                    confidence=0.0,
                    face_area_percent=0.0,
                    quality_score=0.0,
                    fallback_to_original=True,
                    error_message="No faces detected",
                )

            # Select primary face
            face = self.face_detector.get_primary_face(faces)
            if face is None:
                return CropResult(
                    success=False,
                    cropped_path=None,
                    confidence=0.0,
                    face_area_percent=0.0,
                    quality_score=0.0,
                    fallback_to_original=True,
                    error_message="Failed to select primary face",
                )

            # Calculate confidence
            confidence = self.face_detector.calculate_confidence(face, image)

            if confidence < self.MIN_CONFIDENCE:
                logger.warning(
                    f"Low confidence ({confidence:.2f}) for {image_path.name}, skipping crop"
                )
                return CropResult(
                    success=False,
                    cropped_path=None,
                    confidence=confidence,
                    face_area_percent=0.0,
                    quality_score=0.0,
                    fallback_to_original=True,
                    error_message=f"Low confidence: {confidence:.2f}",
                )

            # Calculate crop box
            crop_box = self.calculate_crop_box(face, (width, height))

            # Apply crop
            cropped = self.apply_crop(image, crop_box)

            # Validate crop quality
            face_percent = (face.area / (crop_box.width * crop_box.height)) * 100
            quality_score = self.calculate_quality_score(cropped, face, crop_box, confidence)

            if not self.validate_crop_quality(cropped, face_percent):
                logger.warning(f"Crop quality validation failed for {image_path.name}")
                return CropResult(
                    success=False,
                    cropped_path=None,
                    confidence=confidence,
                    face_area_percent=face_percent,
                    quality_score=quality_score,
                    fallback_to_original=True,
                    error_message="Crop quality validation failed",
                )

            # Resize to target size
            resized = cv2.resize(
                cropped,
                self.target_size,
                interpolation=cv2.INTER_LANCZOS4,
            )

            # Save cropped image
            cv2.imwrite(str(output_path), resized)

            logger.info(
                f"Successfully cropped {image_path.name} -> {output_path.name} "
                f"(confidence={confidence:.2f}, quality={quality_score:.2f})"
            )

            return CropResult(
                success=True,
                cropped_path=str(output_path),
                confidence=confidence,
                face_area_percent=face_percent,
                quality_score=quality_score,
                fallback_to_original=False,
            )

        except Exception as e:
            logger.error(f"Error cropping {image_path}: {e}")
            return CropResult(
                success=False,
                cropped_path=None,
                confidence=0.0,
                face_area_percent=0.0,
                quality_score=0.0,
                fallback_to_original=True,
                error_message=str(e),
            )

    def calculate_crop_box(
        self,
        face: FaceBox,
        image_dims: tuple[int, int],
    ) -> CropBox:
        """
        Calculate optimal crop box with smart padding.

        Args:
            face: Detected face bounding box
            image_dims: Image dimensions (width, height)

        Returns:
            Crop box with intelligent padding
        """
        img_width, img_height = image_dims

        # Calculate padding
        padding_top = int(face.height * self.PADDING_TOP)
        padding_bottom = int(face.height * self.PADDING_BOTTOM)
        padding_sides = int(face.width * self.PADDING_SIDES)

        # Calculate initial crop box
        crop_x = face.x - padding_sides
        crop_y = face.y - padding_top
        crop_width = face.width + (2 * padding_sides)
        crop_height = face.height + padding_top + padding_bottom

        # Force square aspect ratio
        # Use the larger dimension and center the other
        crop_size = max(crop_width, crop_height)

        if crop_width < crop_size:
            # Expand width, keep face centered
            diff = crop_size - crop_width
            crop_x -= diff // 2
            crop_width = crop_size

        if crop_height < crop_size:
            # Expand height, keep face in upper portion
            crop_height = crop_size

        # Ensure crop box is within image bounds
        # If crop extends beyond image, shift it
        if crop_x < 0:
            crop_x = 0
        if crop_y < 0:
            crop_y = 0
        if crop_x + crop_width > img_width:
            crop_x = max(0, img_width - crop_width)
            crop_width = min(crop_width, img_width)
        if crop_y + crop_height > img_height:
            crop_y = max(0, img_height - crop_height)
            crop_height = min(crop_height, img_height)

        return CropBox(
            x=crop_x,
            y=crop_y,
            width=crop_width,
            height=crop_height,
        )

    def apply_crop(
        self,
        image: np.ndarray,
        crop_box: CropBox,
    ) -> np.ndarray:
        """
        Execute crop with edge case handling.

        Args:
            image: Original image as numpy array
            crop_box: Crop box to apply

        Returns:
            Cropped image as numpy array
        """
        y_slice, x_slice = crop_box.to_slice()
        cropped = image[y_slice, x_slice]
        return cropped

    def validate_crop_quality(
        self,
        cropped: np.ndarray,
        face_percent: float,
    ) -> bool:
        """
        Quality gate - ensure crop meets standards.

        Args:
            cropped: Cropped image
            face_percent: Face size as percentage of crop

        Returns:
            True if crop quality is acceptable
        """
        # Check face occupies reasonable portion of crop
        if face_percent < self.MIN_FACE_PERCENT * 100:
            logger.debug(f"Face too small in crop: {face_percent:.1f}%")
            return False

        if face_percent > self.MAX_FACE_PERCENT * 100:
            logger.debug(f"Face too large in crop: {face_percent:.1f}%")
            return False

        # Check crop is not too small
        height, width = cropped.shape[:2]
        if width < 100 or height < 100:
            logger.debug(f"Crop too small: {width}x{height}")
            return False

        return True

    def calculate_quality_score(
        self,
        cropped: np.ndarray,
        face: FaceBox,
        crop_box: CropBox,
        confidence: float,
    ) -> float:
        """
        Calculate composite quality score for the crop.

        Factors:
        - Detection confidence
        - Face size relative to crop
        - Sharpness (Laplacian variance)

        Args:
            cropped: Cropped image
            face: Original face bounding box
            crop_box: Crop box used
            confidence: Face detection confidence

        Returns:
            Quality score between 0 and 1
        """
        # Factor 1: Detection confidence (0-1)
        conf_score = confidence

        # Factor 2: Face size (should be in ideal range)
        face_percent = face.area / (crop_box.width * crop_box.height)
        ideal_percent = (self.MIN_FACE_PERCENT + self.MAX_FACE_PERCENT) / 2
        size_diff = abs(face_percent - ideal_percent)
        size_score = 1.0 - (size_diff / ideal_percent)
        size_score = max(0, min(size_score, 1.0))

        # Factor 3: Sharpness (Laplacian variance)
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Normalize: typical sharp images have variance > 100
        sharpness_score = min(laplacian_var / 100, 1.0)

        # Weighted average
        quality = 0.4 * conf_score + 0.3 * size_score + 0.3 * sharpness_score

        return float(quality)
