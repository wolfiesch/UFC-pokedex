/**
 * Basic face/subject detection for image cropping
 * Uses edge detection and contrast analysis to identify the subject
 */

/**
 * Analyzes an image to find the most likely face/subject center point
 * Uses a simple but effective algorithm:
 * 1. Convert to grayscale
 * 2. Divide into grid cells
 * 3. Calculate contrast/edge density in each cell
 * 4. Find the region with highest activity (likely contains face)
 * 5. Return center point for circular crop
 *
 * @param imageData - ImageData from canvas
 * @returns Object with x, y coordinates (0-1 normalized) for crop center
 */
export function detectSubjectCenter(imageData: ImageData): {
  x: number;
  y: number;
} {
  const { width, height, data } = imageData;

  // Grid size for analysis (smaller = more precise but slower)
  const gridSize = 16;
  const cellWidth = width / gridSize;
  const cellHeight = height / gridSize;

  // Create contrast map
  const contrastMap: number[][] = [];
  for (let i = 0; i < gridSize; i++) {
    contrastMap[i] = [];
    for (let j = 0; j < gridSize; j++) {
      contrastMap[i][j] = 0;
    }
  }

  // Calculate contrast for each grid cell
  for (let cellY = 0; cellY < gridSize; cellY++) {
    for (let cellX = 0; cellX < gridSize; cellX++) {
      let totalContrast = 0;
      let samples = 0;

      // Sample pixels in this cell
      const startX = Math.floor(cellX * cellWidth);
      const startY = Math.floor(cellY * cellHeight);
      const endX = Math.min(Math.floor((cellX + 1) * cellWidth), width);
      const endY = Math.min(Math.floor((cellY + 1) * cellHeight), height);

      // Sample every 4th pixel for performance
      for (let y = startY; y < endY; y += 4) {
        for (let x = startX; x < endX; x += 4) {
          const idx = (y * width + x) * 4;

          // Convert to grayscale
          const gray =
            0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];

          // Check neighboring pixels for contrast
          if (x > 0 && y > 0 && x < width - 1 && y < height - 1) {
            // Right neighbor
            const rightIdx = (y * width + (x + 1)) * 4;
            const rightGray =
              0.299 * data[rightIdx] +
              0.587 * data[rightIdx + 1] +
              0.114 * data[rightIdx + 2];

            // Bottom neighbor
            const bottomIdx = ((y + 1) * width + x) * 4;
            const bottomGray =
              0.299 * data[bottomIdx] +
              0.587 * data[bottomIdx + 1] +
              0.114 * data[bottomIdx + 2];

            // Sum of absolute differences
            totalContrast +=
              Math.abs(gray - rightGray) + Math.abs(gray - bottomGray);
            samples++;
          }
        }
      }

      // Average contrast for this cell
      contrastMap[cellY][cellX] = samples > 0 ? totalContrast / samples : 0;
    }
  }

  // Apply Gaussian-like weighting to prefer center regions
  // (faces are usually more centered in photos)
  const centerX = gridSize / 2;
  const centerY = gridSize / 2;

  for (let cellY = 0; cellY < gridSize; cellY++) {
    for (let cellX = 0; cellX < gridSize; cellX++) {
      // Distance from center
      const dx = cellX - centerX;
      const dy = cellY - centerY;
      const distFromCenter = Math.sqrt(dx * dx + dy * dy);

      // Slight bias toward center (not too strong)
      const centerWeight = 1 + 0.3 * (1 - distFromCenter / (gridSize / 2));

      contrastMap[cellY][cellX] *= centerWeight;
    }
  }

  // Find the cell with highest contrast (likely contains face/subject)
  let maxContrast = 0;
  let maxCellX = Math.floor(gridSize / 2);
  let maxCellY = Math.floor(gridSize / 2);

  for (let cellY = 0; cellY < gridSize; cellY++) {
    for (let cellX = 0; cellX < gridSize; cellX++) {
      if (contrastMap[cellY][cellX] > maxContrast) {
        maxContrast = contrastMap[cellY][cellX];
        maxCellX = cellX;
        maxCellY = cellY;
      }
    }
  }

  // Convert cell coordinates to normalized coordinates (0-1)
  const normalizedX = (maxCellX + 0.5) / gridSize;
  const normalizedY = (maxCellY + 0.5) / gridSize;

  return {
    x: normalizedX,
    y: normalizedY,
  };
}

/**
 * Loads an image and extracts ImageData for analysis
 *
 * @param imageUrl - URL of the image to analyze
 * @returns Promise resolving to ImageData
 */
export async function loadImageData(imageUrl: string): Promise<ImageData> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous"; // Enable CORS if needed

    img.onload = () => {
      // Create temporary canvas for extraction
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;

      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("Failed to get canvas context"));
        return;
      }

      ctx.drawImage(img, 0, 0);

      try {
        const imageData = ctx.getImageData(0, 0, img.width, img.height);
        resolve(imageData);
      } catch (error) {
        reject(error);
      }
    };

    img.onerror = () => {
      reject(new Error(`Failed to load image: ${imageUrl}`));
    };

    img.src = imageUrl;
  });
}

/**
 * Detects subject center in an image and returns crop coordinates
 *
 * @param imageUrl - URL of the image
 * @returns Promise resolving to normalized crop center coordinates
 */
export async function getSmartCropCenter(
  imageUrl: string,
): Promise<{ x: number; y: number }> {
  try {
    const imageData = await loadImageData(imageUrl);
    return detectSubjectCenter(imageData);
  } catch (error) {
    console.warn("Face detection failed, using center crop:", error);
    // Fallback to center
    return { x: 0.5, y: 0.5 };
  }
}

/**
 * Cache for detected crop centers to avoid re-analyzing the same image
 */
const cropCenterCache = new Map<string, { x: number; y: number }>();

/**
 * Get crop center with caching
 *
 * @param imageUrl - URL of the image
 * @returns Promise resolving to crop center (cached if available)
 */
export async function getSmartCropCenterCached(
  imageUrl: string,
): Promise<{ x: number; y: number }> {
  if (cropCenterCache.has(imageUrl)) {
    return cropCenterCache.get(imageUrl)!;
  }

  const center = await getSmartCropCenter(imageUrl);
  cropCenterCache.set(imageUrl, center);
  return center;
}
