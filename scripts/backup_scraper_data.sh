#!/bin/bash
# Backup scraper data with timestamps for preservation and regression detection
#
# Usage:
#   ./scripts/backup_scraper_data.sh                    # Backup current data
#   ./scripts/backup_scraper_data.sh --list             # List all backups
#   ./scripts/backup_scraper_data.sh --compare BACKUP1 BACKUP2  # Compare two backups

set -e

BACKUP_DIR="data/raw/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CURRENT_DATA="data/raw/bfo_odds_batch.jsonl"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to backup current data
backup_data() {
    if [ ! -f "$CURRENT_DATA" ]; then
        echo "❌ No data file found: $CURRENT_DATA"
        exit 1
    fi

    local fight_count=$(wc -l < "$CURRENT_DATA")
    local file_size=$(du -h "$CURRENT_DATA" | cut -f1)

    # Create backup with metadata
    local backup_file="$BACKUP_DIR/bfo_odds_$TIMESTAMP.jsonl"
    local metadata_file="$BACKUP_DIR/bfo_odds_$TIMESTAMP.meta.json"

    # Copy data
    cp "$CURRENT_DATA" "$backup_file"

    # Create metadata
    cat > "$metadata_file" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "fight_count": $fight_count,
  "file_size": "$file_size",
  "source_file": "$CURRENT_DATA",
  "backup_file": "$backup_file",
  "scraper_version": "closing_odds_fix_v1",
  "notes": "Scraper fixed to extract closing odds only (3-element data-li arrays)"
}
EOF

    echo "✅ Backup created:"
    echo "   📁 Data: $backup_file"
    echo "   📋 Meta: $metadata_file"
    echo "   📊 Stats: $fight_count fights, $file_size"
    echo ""
    echo "📝 To restore this backup later:"
    echo "   cp $backup_file $CURRENT_DATA"
}

# Function to list all backups
list_backups() {
    echo "📦 Available backups:"
    echo ""

    for meta_file in "$BACKUP_DIR"/*.meta.json; do
        if [ -f "$meta_file" ]; then
            local timestamp=$(jq -r '.timestamp' "$meta_file")
            local date=$(jq -r '.date' "$meta_file")
            local fight_count=$(jq -r '.fight_count' "$meta_file")
            local file_size=$(jq -r '.file_size' "$meta_file")
            local version=$(jq -r '.scraper_version' "$meta_file")

            echo "📅 $timestamp ($version)"
            echo "   Date: $date"
            echo "   Fights: $fight_count"
            echo "   Size: $file_size"
            echo ""
        fi
    done
}

# Function to compare two backups for regression detection
compare_backups() {
    local backup1="$1"
    local backup2="$2"

    if [ ! -f "$backup1" ]; then
        echo "❌ Backup 1 not found: $backup1"
        exit 1
    fi

    if [ ! -f "$backup2" ]; then
        echo "❌ Backup 2 not found: $backup2"
        exit 1
    fi

    echo "🔍 Comparing backups for regression detection..."
    echo ""

    # Extract a sample fight and compare odds
    local sample_fight_1=$(head -1 "$backup1")
    local sample_fight_2=$(head -1 "$backup2")

    echo "📊 Backup 1 sample:"
    echo "$sample_fight_1" | jq '{f1: .fighter_1.name, f2: .fighter_2.name, fanduel: [.odds.bookmakers[] | select(.bookmaker_id == 21)] | .[0]}'

    echo ""
    echo "📊 Backup 2 sample:"
    echo "$sample_fight_2" | jq '{f1: .fighter_1.name, f2: .fighter_2.name, fanduel: [.odds.bookmakers[] | select(.bookmaker_id == 21)] | .[0]}'

    echo ""
    echo "📈 Statistics comparison:"
    echo "   Backup 1: $(wc -l < "$backup1") fights"
    echo "   Backup 2: $(wc -l < "$backup2") fights"

    # Check for suspicious odds patterns
    echo ""
    echo "🔍 Checking for suspicious odds (regression indicators):"

    local sus1=$(grep -c "+3400\|-10000" "$backup1" || true)
    local sus2=$(grep -c "+3400\|-10000" "$backup2" || true)

    echo "   Backup 1 suspicious odds: $sus1"
    echo "   Backup 2 suspicious odds: $sus2"

    if [ "$sus2" -gt "$sus1" ]; then
        echo "   ⚠️  WARNING: Backup 2 has MORE suspicious odds (possible regression!)"
    elif [ "$sus2" -lt "$sus1" ]; then
        echo "   ✅ Backup 2 has FEWER suspicious odds (improvement!)"
    else
        echo "   ✅ No change in suspicious odds count"
    fi
}

# Main script logic
case "${1:-backup}" in
    backup)
        backup_data
        ;;
    --list)
        list_backups
        ;;
    --compare)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 --compare BACKUP1 BACKUP2"
            exit 1
        fi
        compare_backups "$2" "$3"
        ;;
    *)
        echo "Usage: $0 [backup|--list|--compare BACKUP1 BACKUP2]"
        exit 1
        ;;
esac
