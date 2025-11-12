"""
Suggest gym locations via Photon/OSM to help curate training city/country data.

Example usage:
    python scripts/suggest_gym_location.py --gym "SBG Ireland"
    python scripts/suggest_gym_location.py --input-file data/missing_gyms.txt --country IE --limit 3
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click
import httpx

from scripts.utils.gym_locations import resolve_gym_location

PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "UFC-Pokedex-GymLocator/1.0 (+https://github.com/wolfgangschoenberger/ufc-pokedex)"
DEFAULT_CACHE_FILE = "data/processed/gym_location_cache.json"
DEFAULT_SUGGESTIONS_FILE = "data/processed/gym_location_suggestions.jsonl"
DEFAULT_MAX_CACHE_AGE_DAYS = 7


@dataclass(slots=True)
class GymSuggestion:
    """Structured representation of a Photon suggestion."""

    label: str
    city: str | None
    state: str | None
    country: str | None
    country_code: str | None
    latitude: float | None
    longitude: float | None
    street: str | None
    postcode: str | None
    osm_type: str | None
    osm_id: int | None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source"] = "photon"
        return data


def _normalize(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).strip()


def _load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Cache file {path} is corrupted: {exc}") from exc


def _save_cache(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2))


def _cache_is_fresh(entry: dict[str, Any], max_age_days: int) -> bool:
    timestamp = entry.get("queried_at")
    if not timestamp:
        return False

    try:
        queried_at = datetime.fromisoformat(timestamp)
    except ValueError:
        return False

    return datetime.utcnow() - queried_at < timedelta(days=max_age_days)


def _fetch_photon_suggestions(query: str, limit: int) -> list[GymSuggestion]:
    params = {"q": query, "limit": limit, "lang": "en"}
    headers = {"User-Agent": USER_AGENT}

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = httpx.get(PHOTON_URL, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
            suggestions: list[GymSuggestion] = []
            for feature in payload.get("features", []):
                props = feature.get("properties", {}) or {}
                coords = feature.get("geometry", {}).get("coordinates", [None, None])

                suggestion = GymSuggestion(
                    label=props.get("name") or query,
                    city=props.get("city") or props.get("county"),
                    state=props.get("state"),
                    country=props.get("country"),
                    country_code=(props.get("countrycode") or "").upper() or None,
                    latitude=coords[1] if len(coords) == 2 else None,
                    longitude=coords[0] if len(coords) == 2 else None,
                    street=props.get("street"),
                    postcode=props.get("postcode"),
                    osm_type=props.get("osm_type"),
                    osm_id=props.get("osm_id"),
                )
                suggestions.append(suggestion)
            return suggestions
        except httpx.HTTPError as exc:
            last_error = exc
            sleep_for = min(2 ** attempt, 10)
            click.echo(f"Photon lookup failed (attempt {attempt + 1}/3): {exc}. Retrying in {sleep_for}s…")
            time.sleep(sleep_for)

    raise click.ClickException(f"Photon lookup failed after 3 attempts: {last_error}")


def _filter_by_country(
    suggestions: list[GymSuggestion],
    country_filters: tuple[str, ...],
) -> list[GymSuggestion]:
    if not country_filters:
        return suggestions

    normalized_filters = tuple(f.strip().lower() for f in country_filters if f.strip())
    filtered = [
        s
        for s in suggestions
        if (
            s.country_code and s.country_code.lower() in normalized_filters
            or s.country and s.country.lower() in normalized_filters
        )
    ]
    return filtered or suggestions


def _append_suggestion_record(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload))
        handle.write("\n")


def _collect_gym_names(gym_names: tuple[str, ...], input_file: str | None) -> list[str]:
    names: list[str] = []
    names.extend(gym_names)

    if input_file:
        file_path = Path(input_file)
        if not file_path.exists():
            raise click.BadParameter(f"Input file not found: {input_file}")
        with file_path.open() as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                names.append(stripped)

    ordered: list[str] = []
    seen = set()
    for name in names:
        normalized = _normalize(name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(name.strip())
    return ordered


@click.command()
@click.option("--gym", "-g", multiple=True, help="Gym name to look up (repeatable).")
@click.option(
    "--input-file",
    "-i",
    type=click.Path(exists=True, dir_okay=False),
    help="Optional file containing one gym name per line.",
)
@click.option(
    "--country",
    "-c",
    multiple=True,
    help="Preferred country name or ISO2 code to filter suggestions.",
)
@click.option("--limit", default=5, show_default=True, help="Maximum suggestions per gym.")
@click.option(
    "--cache-file",
    default=DEFAULT_CACHE_FILE,
    show_default=True,
    help="Where to store cached Photon responses.",
)
@click.option(
    "--suggestions-file",
    default=DEFAULT_SUGGESTIONS_FILE,
    show_default=True,
    help="Append structured suggestions to this JSONL file.",
)
@click.option(
    "--max-age-days",
    default=DEFAULT_MAX_CACHE_AGE_DAYS,
    show_default=True,
    help="Refresh cache entries older than this many days.",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Ignore cached responses and re-query Photon.",
)
@click.option(
    "--include-known",
    is_flag=True,
    help="Also run suggestions for gyms already in gym_locations.csv.",
)
def main(
    gym: tuple[str, ...],
    input_file: str | None,
    country: tuple[str, ...],
    limit: int,
    cache_file: str,
    suggestions_file: str,
    max_age_days: int,
    force_refresh: bool,
    include_known: bool,
):
    """Suggest training gym locations to speed up manual curation."""
    gyms = _collect_gym_names(gym, input_file)
    if not gyms:
        raise click.ClickException("Provide at least one gym name or an input file.")

    cache_path = Path(cache_file)
    cache = _load_cache(cache_path)

    suggestions_path = Path(suggestions_file)
    processed = 0

    for name in gyms:
        normalized = _normalize(name)
        existing = resolve_gym_location(name)
        if existing and not include_known:
            click.echo(
                f"✅ {name} already mapped to {existing.city or '-'}, {existing.country or '-'} "
                "(use --include-known to force lookup)."
            )
            continue

        processed += 1

        cached_entry = cache.get(normalized)
        if not force_refresh and cached_entry and _cache_is_fresh(cached_entry, max_age_days):
            raw_results = cached_entry.get("results", [])
            suggestions = [
                GymSuggestion(
                    label=item.get("label"),
                    city=item.get("city"),
                    state=item.get("state"),
                    country=item.get("country"),
                    country_code=item.get("country_code"),
                    latitude=item.get("latitude"),
                    longitude=item.get("longitude"),
                    street=item.get("street"),
                    postcode=item.get("postcode"),
                    osm_type=item.get("osm_type"),
                    osm_id=item.get("osm_id"),
                )
                for item in raw_results
            ]
            from_cache = True
        else:
            suggestions = _fetch_photon_suggestions(name, limit)
            cache[normalized] = {
                "queried_at": datetime.utcnow().isoformat(),
                "results": [s.as_dict() for s in suggestions],
            }
            from_cache = False

        filtered = _filter_by_country(suggestions, country)
        origin = "cache" if from_cache else "live"
        click.echo(f"\n{name}  ({origin})")
        separator_len = max(len(name) + len(origin) + 3, 5)
        click.echo("-" * separator_len)

        if not filtered:
            click.echo("  No suggestions found.")
            continue

        for idx, suggestion in enumerate(filtered, start=1):
            location_bits = [bit for bit in [suggestion.city, suggestion.state, suggestion.country] if bit]
            location = ", ".join(location_bits) if location_bits else "Unknown"
            if suggestion.latitude is not None and suggestion.longitude is not None:
                coords = f"{suggestion.latitude:.4f}, {suggestion.longitude:.4f}"
            else:
                coords = "n/a"
            click.echo(
                f"  {idx}. {location} "
                f"[{suggestion.country_code or '--'}] "
                f"@ {coords} "
                f"(OSM: {suggestion.osm_type or '?'}:{suggestion.osm_id or '?'})"
            )
            if suggestion.street or suggestion.postcode:
                click.echo(
                    f"     {suggestion.street or ''} {suggestion.postcode or ''}".strip()
                )

        record = {
            "gym_name": name,
            "generated_at": datetime.utcnow().isoformat(),
            "source": origin,
            "suggestions": [s.as_dict() for s in filtered],
        }
        _append_suggestion_record(suggestions_path, record)

    _save_cache(cache_path, cache)
    click.echo(f"\nDone. Generated suggestions for {processed} gyms.")


if __name__ == "__main__":
    main()
