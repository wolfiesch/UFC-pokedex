import { useEffect, useState } from "react";

import { imageCache } from "@/lib/utils/imageCache";
import type { ScatterFight } from "@/types/fight-scatter";

/**
 * Preloads opponent imagery (or initials placeholders) so the canvas renderer
 * can draw synchronously without awaiting async decode pipelines.
 */
export function useOpponentImagePreload(fights: ScatterFight[]): boolean {
  const [imagesLoaded, setImagesLoaded] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const loadImages = async () => {
      const tasks = fights.map((fight) => {
        if (fight.opponent_id) {
          return imageCache.getOpponentBitmap(
            fight.opponent_id,
            fight.headshot_url,
            fight.opponent_name
          );
        }
        return Promise.resolve(null);
      });

      try {
        await Promise.all(tasks);
        if (isMounted) {
          setImagesLoaded(true);
        }
      } catch (error) {
        console.warn("Failed to preload fight scatter images", error);
        if (isMounted) {
          setImagesLoaded(true);
        }
      }
    };

    setImagesLoaded(false);
    void loadImages();

    return () => {
      isMounted = false;
    };
  }, [fights]);

  return imagesLoaded;
}
