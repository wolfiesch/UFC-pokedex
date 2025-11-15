#!/usr/bin/env python3
"""AI-powered image validation using GPT-4o-mini Vision API.

This script validates fighter images by detecting:
- Illustrations, cartoons, paintings (not real photos)
- Stock photo watermarks (Getty, Alamy, Shutterstock, etc.)
- Wrong subjects (not actual UFC fighters)
- Multiple people in frame
- Non-athletic/unprofessional settings

Cost estimate: ~$0.21 for 4,633 images using GPT-4o-mini.

Usage:
    # Validate all fighters
    python scripts/ai_image_validator.py

    # Validate specific fighters
    python scripts/ai_image_validator.py --fighter-ids abc123,def456

    # Test mode (first 10 images only)
    python scripts/ai_image_validator.py --test

    # Resume from previous run
    python scripts/ai_image_validator.py --resume
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import asyncio
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db.connection import get_session_factory
from backend.db.models import Fighter


# Validation prompt for GPT-4o-mini
VALIDATION_PROMPT = """Analyze this UFC fighter image and determine if it's valid.

A VALID image must be:
✓ A real photograph (not illustration, cartoon, painting, or drawing)
✓ Of a single person
✓ Professional quality (athlete headshot or promotional photo)
✓ No stock photo watermarks (Alamy, Getty, Shutterstock, etc.)

INVALID examples:
✗ Historical illustrations or paintings
✗ Cartoons or anime-style drawings
✗ Stock photos with watermarks
✗ Multiple people in frame
✗ Non-athletic settings (e.g., business portraits, casual photos)
✗ Not a real person (CGI, avatar, etc.)

Respond in JSON format ONLY:
{
  "valid": true/false,
  "confidence": 0-100,
  "reason": "Brief explanation if invalid",
  "issues": ["list", "of", "specific", "problems"]
}

Examples:
- Historical painting → {"valid": false, "confidence": 100, "reason": "Historical illustration, not a photograph", "issues": ["painting", "not_real_photo"]}
- Real fighter photo → {"valid": true, "confidence": 95, "reason": "Professional athlete headshot", "issues": []}
- Stock photo → {"valid": false, "confidence": 90, "reason": "Contains Alamy watermark", "issues": ["watermark"]}
"""


class AIImageValidator:
    """Validates fighter images using GPT-4o-mini Vision API."""

    def __init__(
        self,
        api_key: str | None = None,
        image_root: Path | None = None,
        output_dir: Path | None = None,
    ):
        """Initialize the AI image validator.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            image_root: Root directory containing fighter images
            output_dir: Directory for validation reports
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = AsyncOpenAI(api_key=self.api_key)

        # Default to project root / data / images / fighters
        if image_root is None:
            project_root = Path(__file__).resolve().parents[1]
            image_root = project_root / "data" / "images" / "fighters"
        self.image_root = image_root

        # Output directory for reports
        if output_dir is None:
            project_root = Path(__file__).resolve().parents[1]
            output_dir = project_root / "data" / "validation_reports"
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Resume state file
        self.state_file = self.output_dir / "ai_validation_state.json"

        # Track statistics
        self.stats = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "errors": 0,
            "total_cost": 0.0,
        }

    async def validate_image(self, fighter_id: str, fighter_name: str) -> dict[str, Any] | None:
        """Validate a single fighter image using GPT-4o-mini.

        Args:
            fighter_id: Fighter ID (used as filename)
            fighter_name: Fighter name (for reporting)

        Returns:
            Validation result dict or None if image not found
        """
        # Find image file
        image_path = self._find_image_path(fighter_id)
        if not image_path:
            print(f"  ⚠️  Image not found: {fighter_id} ({fighter_name})")
            return None

        try:
            # Encode image to base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Determine image format
            ext = image_path.suffix.lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }.get(ext, "image/jpeg")

            # Call GPT-4o-mini Vision API
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VALIDATION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}",
                                    "detail": "low",  # Low detail = cheaper + faster
                                },
                            },
                        ],
                    }
                ],
                max_tokens=200,
                temperature=0.0,  # Deterministic responses
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from API")

            # Extract JSON from response (handle markdown code blocks)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)

            # Calculate cost (GPT-4o-mini pricing)
            # Input: $0.15 per 1M tokens, Output: $0.60 per 1M tokens
            # Low detail images: ~85 tokens
            input_tokens = response.usage.prompt_tokens if response.usage else 85
            output_tokens = response.usage.completion_tokens if response.usage else 50
            cost = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)
            self.stats["total_cost"] += cost

            # Add metadata
            result["fighter_id"] = fighter_id
            result["fighter_name"] = fighter_name
            result["image_path"] = str(image_path.relative_to(self.image_root.parent))
            result["validated_at"] = datetime.now(UTC).isoformat()
            result["cost"] = cost

            # Update stats
            if result["valid"]:
                self.stats["valid"] += 1
            else:
                self.stats["invalid"] += 1

            return result

        except Exception as e:
            print(f"  ❌ Error validating {fighter_id} ({fighter_name}): {e}")
            self.stats["errors"] += 1
            return {
                "fighter_id": fighter_id,
                "fighter_name": fighter_name,
                "valid": None,
                "error": str(e),
                "validated_at": datetime.now(UTC).isoformat(),
            }

    async def validate_batch(
        self,
        fighters: list[tuple[str, str]],
        batch_size: int = 10,
        resume: bool = False,
    ) -> list[dict[str, Any]]:
        """Validate a batch of fighter images with rate limiting.

        Args:
            fighters: List of (fighter_id, fighter_name) tuples
            batch_size: Number of concurrent API requests
            resume: Resume from previous run

        Returns:
            List of validation results
        """
        results = []

        # Load resume state
        processed_ids = set()
        if resume and self.state_file.exists():
            with open(self.state_file, "r") as f:
                state = json.load(f)
                processed_ids = set(state.get("processed_ids", []))
                print(f"📂 Resuming from previous run ({len(processed_ids)} already processed)")

        # Filter out already processed
        fighters_to_process = [
            (fid, fname) for fid, fname in fighters if fid not in processed_ids
        ]

        if not fighters_to_process:
            print("✅ All fighters already processed!")
            return results

        self.stats["total"] = len(fighters_to_process)
        print(f"🔍 Validating {len(fighters_to_process)} fighter images...")
        print(f"💰 Estimated cost: ${len(fighters_to_process) * 0.00005:.4f}\n")

        # Process in batches to respect rate limits
        for i in range(0, len(fighters_to_process), batch_size):
            batch = fighters_to_process[i : i + batch_size]

            # Process batch concurrently
            tasks = [self.validate_image(fid, fname) for fid, fname in batch]
            batch_results = await asyncio.gather(*tasks)

            # Filter out None results
            batch_results = [r for r in batch_results if r is not None]
            results.extend(batch_results)

            # Update processed IDs
            processed_ids.update(fid for fid, _ in batch)

            # Save progress
            self._save_state(processed_ids)

            # Progress update
            progress = i + len(batch)
            print(
                f"  Progress: {progress}/{len(fighters_to_process)} "
                f"({progress/len(fighters_to_process)*100:.1f}%) | "
                f"Cost so far: ${self.stats['total_cost']:.4f}"
            )

            # Small delay to respect rate limits (optional)
            await asyncio.sleep(0.1)

        return results

    def generate_report(self, results: list[dict[str, Any]]) -> Path:
        """Generate validation report.

        Args:
            results: List of validation results

        Returns:
            Path to generated report
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"ai_validation_report_{timestamp}.json"

        # Separate valid and invalid
        invalid_images = [r for r in results if r.get("valid") is False]
        valid_images = [r for r in results if r.get("valid") is True]
        errors = [r for r in results if r.get("valid") is None]

        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total_analyzed": len(results),
                "valid": len(valid_images),
                "invalid": len(invalid_images),
                "errors": len(errors),
                "total_cost": self.stats["total_cost"],
            },
            "invalid_images": sorted(invalid_images, key=lambda x: x.get("confidence", 0), reverse=True),
            "errors": errors,
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n📊 Report generated: {report_file}")

        # Also generate human-readable summary
        summary_file = self.output_dir / f"ai_validation_summary_{timestamp}.txt"
        with open(summary_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("AI Image Validation Report\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"Total analyzed: {len(results)}\n")
            f.write(f"Valid: {len(valid_images)} ({len(valid_images)/len(results)*100:.1f}%)\n")
            f.write(f"Invalid: {len(invalid_images)} ({len(invalid_images)/len(results)*100:.1f}%)\n")
            f.write(f"Errors: {len(errors)}\n")
            f.write(f"Total cost: ${self.stats['total_cost']:.4f}\n\n")

            if invalid_images:
                f.write("=" * 80 + "\n")
                f.write("INVALID IMAGES (requires manual review)\n")
                f.write("=" * 80 + "\n\n")

                for img in invalid_images:
                    f.write(f"Fighter: {img['fighter_name']} (ID: {img['fighter_id']})\n")
                    f.write(f"Confidence: {img.get('confidence', 0)}%\n")
                    f.write(f"Reason: {img.get('reason', 'N/A')}\n")
                    f.write(f"Issues: {', '.join(img.get('issues', []))}\n")
                    f.write(f"Path: {img['image_path']}\n")
                    f.write("-" * 80 + "\n")

        print(f"📄 Summary generated: {summary_file}")

        return report_file

    def _find_image_path(self, fighter_id: str) -> Path | None:
        """Find image file for a fighter ID."""
        extensions = [".jpg", ".jpeg", ".png", ".webp"]
        for ext in extensions:
            candidate = self.image_root / f"{fighter_id}{ext}"
            if candidate.exists():
                return candidate
        return None

    def _save_state(self, processed_ids: set[str]) -> None:
        """Save resume state."""
        with open(self.state_file, "w") as f:
            json.dump({"processed_ids": list(processed_ids)}, f)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI-powered fighter image validation")
    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--fighter-ids",
        type=str,
        help="Comma-separated list of fighter IDs to validate",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode (validate first 10 images only)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous run",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of concurrent API requests (default: 10)",
    )

    args = parser.parse_args()

    # Initialize validator (with optional API key from command line)
    try:
        validator = AIImageValidator(api_key=args.api_key)

        # Test API key by making a simple request
        print("🔑 Testing OpenAI API key...")
        test_client = AsyncOpenAI(api_key=validator.api_key)
        try:
            await test_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            print("✅ API key is valid!\n")
        except Exception as e:
            print(f"❌ API key test failed: {e}")
            print("\nPlease check:")
            print("  1. Your API key is correct (starts with 'sk-proj-' or 'sk-')")
            print("  2. You have credits available: https://platform.openai.com/account/billing")
            print("  3. The key has permissions to use GPT-4o-mini")
            return

    except ValueError as e:
        print(f"❌ {e}")
        print("\nSet your API key using one of these methods:")
        print("  1. Environment variable: export OPENAI_API_KEY='sk-proj-...'")
        print("  2. Command line: --api-key 'sk-proj-...'")
        print("\nGet your API key at: https://platform.openai.com/api-keys")
        return

    # Get fighters from database
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Build query
        query = select(Fighter.id, Fighter.name).where(Fighter.image_url.isnot(None))

        if args.fighter_ids:
            fighter_ids = [fid.strip() for fid in args.fighter_ids.split(",")]
            query = query.where(Fighter.id.in_(fighter_ids))

        query = query.order_by(Fighter.name)

        result = await session.execute(query)
        fighters = [(row.id, row.name) for row in result]

    if not fighters:
        print("❌ No fighters found to validate")
        return

    # Test mode
    if args.test:
        fighters = fighters[:10]
        print("🧪 TEST MODE: Validating first 10 images only\n")

    # Run validation
    results = await validator.validate_batch(
        fighters,
        batch_size=args.batch_size,
        resume=args.resume,
    )

    # Generate report
    if results:
        validator.generate_report(results)

        # Print summary
        print("\n" + "=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)
        print(f"✅ Valid: {validator.stats['valid']}")
        print(f"❌ Invalid: {validator.stats['invalid']}")
        print(f"⚠️  Errors: {validator.stats['errors']}")
        print(f"💰 Total cost: ${validator.stats['total_cost']:.4f}")
    else:
        print("\n⚠️  No results to report")


if __name__ == "__main__":
    asyncio.run(main())
