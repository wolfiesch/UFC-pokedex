#!/bin/bash
# Download images for high-profile fighters with known Sherdog pages

set -e

# Define mappings (fighter_id:sherdog_url)
declare -A FIGHTERS
FIGHTERS[="6506c1d34da9c013"]="https://www.sherdog.com/fighter/Georges-St-Pierre-3500"
FIGHTERS["07f72a2a7591b409"]="https://www.sherdog.com/fighter/Jon-Jones-27944"
FIGHTERS["c849740a3ff51931"]="https://www.sherdog.com/fighter/TJ-Dillashaw-38553"
FIGHTERS["73c7cfa551289285"]="https://www.sherdog.com/fighter/BJ-Penn-1307"
FIGHTERS["5d7bdab5e03e3216"]="https://www.sherdog.com/fighter/CB-Dollaway-22455"
FIGHTERS["749f572d1d3161fb"]="https://www.sherdog.com/fighter/Khalil-Rountree-Jr-73859"
FIGHTERS["98c23cb6da5b3352"]="https://www.sherdog.com/fighter/Aleksei-Oleinik-22653"
FIGHTERS["8e382b585a92affe"]="https://www.sherdog.com/fighter/Phil-Rowe-194685"

IMAGES_DIR="data/images/fighters"
mkdir -p "$IMAGES_DIR"

for fighter_id in "${!FIGHTERS[@]}"; do
    sherdog_url="${FIGHTERS[$fighter_id]}"
    echo "Processing $fighter_id from $sherdog_url"

    # Download page and extract image URL
    image_url=$(curl -s -A "Mozilla/5.0" "$sherdog_url" | \
        grep -oP 'class="module bio_fighter".*?<img.*?src="\K[^"]+' | head -1)

    if [ -n "$image_url" ]; then
        # Make URL absolute if relative
        if [[ "$image_url" != http* ]]; then
            image_url="https://www.sherdog.com${image_url}"
        fi

        # Download image
        curl -s -A "Mozilla/5.0" "$image_url" -o "${IMAGES_DIR}/${fighter_id}.jpg"

        if [ -f "${IMAGES_DIR}/${fighter_id}.jpg" ]; then
            echo "  ✓ Downloaded ${fighter_id}.jpg"
        fi
    else
        echo "  ✗ Could not find image URL"
    fi

    sleep 2  # Rate limit
done

echo ""
echo "✓ Done! Now run: PYTHONPATH=. .venv/bin/python scripts/sync_images_to_db.py"
