"""Image validation service for fighter images.

This module provides facial detection, quality analysis, and duplicate detection
for fighter images stored in data/images/fighters/.

Features:
- Face detection using OpenCV Haar Cascades and MediaPipe
- Quality metrics: resolution, blur detection, brightness
- Duplicate detection via perceptual hashing
- Validation flag generation for problematic images
"""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

# Image validation thresholds
MIN_RESOLUTION_WIDTH = 150
MIN_RESOLUTION_HEIGHT = 150
BLUR_THRESHOLD = 100.0  # Laplacian variance threshold
MIN_BRIGHTNESS = 30
MAX_BRIGHTNESS = 225
DUPLICATE_HASH_THRESHOLD = 5  # Hamming distance for perceptual hash


@dataclass
class ImageValidationResult:
    """Result of image validation analysis."""

    # Basic metrics
    width: int
    height: int
    quality_score: float  # 0-100
    has_face: bool
    face_count: int
    face_encoding: bytes | None

    # Quality metrics
    blur_score: float
    brightness: float

    # Validation flags
    flags: dict[str, Any]

    # Perceptual hash for duplicate detection
    perceptual_hash: str


class ImageValidator:
    """Validates fighter images for quality and detects faces."""

    def __init__(self, image_root: Path | None = None):
        """Initialize the image validator.

        Args:
            image_root: Root directory containing fighter images.
                       Defaults to data/images/fighters/.
        """
        if image_root is None:
            # Default to project root / data / images / fighters
            project_root = Path(__file__).resolve().parents[2]
            image_root = project_root / "data" / "images" / "fighters"

        self.image_root = image_root

        # Initialize face detector (Haar Cascade - fast and reliable)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        if self.face_cascade.empty():
            raise RuntimeError(
                f"Failed to load Haar Cascade from {cascade_path}. "
                "Ensure OpenCV is installed with cascade files."
            )

    def validate_image(self, fighter_id: str) -> ImageValidationResult | None:
        """Validate a single fighter image.

        Args:
            fighter_id: Fighter ID (used as filename stem).

        Returns:
            ImageValidationResult if image exists, None otherwise.
        """
        # Find image file
        image_path = self._find_image_path(fighter_id)
        if not image_path:
            return None

        try:
            # Load image
            pil_image = Image.open(image_path)
            cv_image = cv2.imread(str(image_path))

            if cv_image is None:
                return None

            # Basic metrics
            width, height = pil_image.size
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

            # Face detection
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            has_face = len(faces) > 0
            face_count = len(faces)

            # Face encoding for duplicate detection (using first detected face)
            face_encoding = None
            if has_face:
                face_encoding = self._extract_face_encoding(cv_image, faces[0])

            # Quality metrics
            blur_score = self._calculate_blur(gray)
            brightness = self._calculate_brightness(gray)

            # Calculate overall quality score (0-100)
            quality_score = self._calculate_quality_score(
                width, height, blur_score, brightness, has_face
            )

            # Generate validation flags
            flags = self._generate_flags(
                width, height, has_face, face_count, blur_score, brightness
            )

            # Perceptual hash for duplicate detection
            perceptual_hash = self._calculate_perceptual_hash(pil_image)

            return ImageValidationResult(
                width=width,
                height=height,
                quality_score=quality_score,
                has_face=has_face,
                face_count=face_count,
                face_encoding=face_encoding,
                blur_score=blur_score,
                brightness=brightness,
                flags=flags,
                perceptual_hash=perceptual_hash,
            )

        except Exception as e:
            print(f"Error validating image {fighter_id}: {e}")
            return None

    def find_duplicates(self, fighter_hashes: dict[str, str]) -> dict[str, list[str]]:
        """Find potential duplicate images based on perceptual hashes.

        Args:
            fighter_hashes: Dict mapping fighter_id to perceptual_hash.

        Returns:
            Dict mapping fighter_id to list of potential duplicate fighter_ids.
        """
        duplicates: dict[str, list[str]] = {}

        fighter_ids = list(fighter_hashes.keys())
        for i, fighter_id in enumerate(fighter_ids):
            hash1 = fighter_hashes[fighter_id]

            for other_id in fighter_ids[i + 1 :]:
                hash2 = fighter_hashes[other_id]

                # Calculate Hamming distance between hashes
                distance = self._hamming_distance(hash1, hash2)

                if distance <= DUPLICATE_HASH_THRESHOLD:
                    # Potential duplicate found
                    duplicates.setdefault(fighter_id, []).append(other_id)
                    duplicates.setdefault(other_id, []).append(fighter_id)

        return duplicates

    def _find_image_path(self, fighter_id: str) -> Path | None:
        """Find image file for a fighter ID."""
        extensions = [".jpg", ".jpeg", ".png", ".webp"]
        for ext in extensions:
            candidate = self.image_root / f"{fighter_id}{ext}"
            if candidate.exists():
                return candidate
        return None

    def _calculate_blur(self, gray_image: np.ndarray) -> float:
        """Calculate blur score using Laplacian variance.

        Higher values = sharper image.
        Lower values = blurrier image.
        """
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        variance = laplacian.var()
        return float(variance)

    def _calculate_brightness(self, gray_image: np.ndarray) -> float:
        """Calculate average brightness of image (0-255)."""
        return float(gray_image.mean())

    def _calculate_quality_score(
        self,
        width: int,
        height: int,
        blur_score: float,
        brightness: float,
        has_face: bool,
    ) -> float:
        """Calculate overall quality score (0-100).

        Factors:
        - Resolution: 30 points
        - Sharpness: 30 points
        - Brightness: 20 points
        - Face detection: 20 points
        """
        score = 0.0

        # Resolution score (0-30)
        min_dim = min(width, height)
        if min_dim >= 400:
            score += 30
        elif min_dim >= 300:
            score += 25
        elif min_dim >= 200:
            score += 20
        elif min_dim >= MIN_RESOLUTION_WIDTH:
            score += 10

        # Sharpness score (0-30)
        if blur_score >= 500:
            score += 30
        elif blur_score >= 300:
            score += 25
        elif blur_score >= BLUR_THRESHOLD:
            score += 15
        else:
            score += 5

        # Brightness score (0-20)
        if MIN_BRIGHTNESS <= brightness <= MAX_BRIGHTNESS:
            score += 20
        elif brightness < MIN_BRIGHTNESS or brightness > MAX_BRIGHTNESS:
            score += 10

        # Face detection score (0-20)
        if has_face:
            score += 20

        return min(score, 100.0)

    def _generate_flags(
        self,
        width: int,
        height: int,
        has_face: bool,
        face_count: int,
        blur_score: float,
        brightness: float,
    ) -> dict[str, Any]:
        """Generate validation flags for problematic images."""
        flags: dict[str, Any] = {}

        # Low resolution
        if width < MIN_RESOLUTION_WIDTH or height < MIN_RESOLUTION_HEIGHT:
            flags["low_resolution"] = {
                "width": width,
                "height": height,
                "threshold": f"{MIN_RESOLUTION_WIDTH}x{MIN_RESOLUTION_HEIGHT}",
            }

        # No face detected
        if not has_face:
            flags["no_face_detected"] = True

        # Multiple faces
        if face_count > 1:
            flags["multiple_faces"] = {"count": face_count}

        # Blurry image
        if blur_score < BLUR_THRESHOLD:
            flags["blurry_image"] = {
                "blur_score": blur_score,
                "threshold": BLUR_THRESHOLD,
            }

        # Poor brightness
        if brightness < MIN_BRIGHTNESS:
            flags["too_dark"] = {"brightness": brightness, "threshold": MIN_BRIGHTNESS}
        elif brightness > MAX_BRIGHTNESS:
            flags["too_bright"] = {
                "brightness": brightness,
                "threshold": MAX_BRIGHTNESS,
            }

        return flags

    def _calculate_perceptual_hash(self, pil_image: Image.Image) -> str:
        """Calculate perceptual hash (pHash) for duplicate detection.

        Returns hex string of 64-bit hash.
        """
        # Resize to 32x32
        img = pil_image.convert("L").resize((32, 32), Image.Resampling.LANCZOS)

        # Convert to numpy array
        pixels = np.array(img).flatten()

        # Compute DCT (Discrete Cosine Transform)
        dct = cv2.dct(np.float32(pixels.reshape(32, 32)))

        # Extract top-left 8x8 (low frequencies)
        dct_low = dct[:8, :8]

        # Calculate median
        median = np.median(dct_low)

        # Generate hash: 1 if value > median, 0 otherwise
        hash_bits = (dct_low > median).flatten()

        # Convert to hex string
        hash_int = int("".join(["1" if b else "0" for b in hash_bits]), 2)
        return format(hash_int, "016x")

    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hex hash strings."""
        if len(hash1) != len(hash2):
            return len(hash1) * 4  # Max distance

        # Convert hex to binary
        bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
        bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)

        # Count differing bits
        return sum(b1 != b2 for b1, b2 in zip(bin1, bin2))

    def _extract_face_encoding(
        self, cv_image: np.ndarray, face_rect: tuple[int, int, int, int]
    ) -> bytes | None:
        """Extract face encoding from detected face region.

        Uses simple approach: histogram of face region.
        For production, consider using face_recognition library for better encodings.
        """
        try:
            x, y, w, h = face_rect

            # Extract face region
            face_region = cv_image[y : y + h, x : x + w]

            # Convert to grayscale
            gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)

            # Resize to standard size
            resized = cv2.resize(gray_face, (64, 64))

            # Calculate histogram
            hist = cv2.calcHist([resized], [0], None, [256], [0, 256])
            hist = hist.flatten()

            # Normalize
            hist = hist / hist.sum()

            # Serialize to bytes
            return pickle.dumps(hist)

        except Exception:
            return None


__all__ = ["ImageValidator", "ImageValidationResult"]
