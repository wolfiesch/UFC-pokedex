# AI Image Validator - Usage Guide

## Overview

The AI Image Validator uses GPT-4o-mini's vision capabilities to detect problematic fighter images that traditional validation (face detection, blur, etc.) cannot catch:

- **Illustrations/cartoons/paintings** (like the Muhammad Naimov case)
- **Stock photo watermarks** (Getty, Alamy, Shutterstock)
- **Wrong subjects** (not actual fighters)
- **Multiple people in frame**
- **Non-professional settings**

## Cost

**~$0.21 total** for all 4,633 fighter images using GPT-4o-mini.

## Setup

### 1. Get an OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add $5-10 credit to your account (more than enough for this project)

### 2. Set Environment Variable

```bash
export OPENAI_API_KEY="sk-proj-..."
```

Or add to your `.env` file:
```
OPENAI_API_KEY=sk-proj-...
```

## Usage

### Test Mode (First 10 Images)

```bash
python scripts/ai_image_validator.py --test
```

### Validate Specific Fighters

```bash
# Muhammad Naimov (the problematic illustration)
python scripts/ai_image_validator.py --fighter-ids "8d11d9c13e2ccdf7"

# Multiple fighters
python scripts/ai_image_validator.py --fighter-ids "8d11d9c13e2ccdf7,abc123,def456"
```

### Validate ALL Fighters (~$0.21)

```bash
python scripts/ai_image_validator.py
```

### Resume Interrupted Run

```bash
python scripts/ai_image_validator.py --resume
```

### Adjust Batch Size (Rate Limiting)

```bash
# Process 20 images concurrently (faster but may hit rate limits)
python scripts/ai_image_validator.py --batch-size 20

# Process 5 images at a time (slower but safer)
python scripts/ai_image_validator.py --batch-size 5
```

## Output

The script generates two files in `data/validation_reports/`:

### 1. JSON Report (`ai_validation_report_TIMESTAMP.json`)

```json
{
  "generated_at": "2025-01-15T12:00:00Z",
  "summary": {
    "total_analyzed": 4633,
    "valid": 4520,
    "invalid": 113,
    "errors": 0,
    "total_cost": 0.2134
  },
  "invalid_images": [
    {
      "fighter_id": "8d11d9c13e2ccdf7",
      "fighter_name": "Muhammad Naimov",
      "valid": false,
      "confidence": 100,
      "reason": "Historical illustration, not a photograph",
      "issues": ["painting", "not_real_photo"],
      "image_path": "data/images/fighters/8d11d9c13e2ccdf7.jpg",
      "validated_at": "2025-01-15T12:00:00Z",
      "cost": 0.000046
    }
  ]
}
```

### 2. Human-Readable Summary (`ai_validation_summary_TIMESTAMP.txt`)

```
================================================================================
AI Image Validation Report
================================================================================

Generated: 2025-01-15 12:00:00 UTC
Total analyzed: 4633
Valid: 4520 (97.6%)
Invalid: 113 (2.4%)
Errors: 0
Total cost: $0.2134

================================================================================
INVALID IMAGES (requires manual review)
================================================================================

Fighter: Muhammad Naimov (ID: 8d11d9c13e2ccdf7)
Confidence: 100%
Reason: Historical illustration, not a photograph
Issues: painting, not_real_photo
Path: data/images/fighters/8d11d9c13e2ccdf7.jpg
--------------------------------------------------------------------------------
```

## Next Steps After Validation

1. **Review the report** - Check `data/validation_reports/ai_validation_summary_*.txt`
2. **Fix invalid images** - Use the `/managing-fighter-images` skill to re-download
3. **Update database** - Flag or delete invalid images
4. **Re-run validation** - Use `--resume` to skip already-processed images

## Troubleshooting

### "OPENAI_API_KEY not set" Error

```bash
export OPENAI_API_KEY="sk-proj-..."
python scripts/ai_image_validator.py --test
```

### Rate Limit Errors

Reduce batch size:
```bash
python scripts/ai_image_validator.py --batch-size 5
```

### Out of Credits

Add more credits at https://platform.openai.com/account/billing

## Integration with Existing Validation

The AI validator complements the existing OpenCV-based validator (`backend/services/image_validator.py`):

| Validation Type | Detects | Method |
|----------------|---------|--------|
| **Technical** | Low resolution, blur, brightness, no face | OpenCV (free, fast) |
| **Content** | Cartoons, illustrations, watermarks, wrong subjects | GPT-4o-mini ($0.21 total) |

You can run both:
1. Run technical validation first (free, filters obvious bad images)
2. Run AI validation on remaining images (catches edge cases like the Muhammad Naimov illustration)

## Example Workflow

```bash
# 1. Test on a few known-bad images
python scripts/ai_image_validator.py --fighter-ids "8d11d9c13e2ccdf7" --test

# 2. Validate a larger batch
python scripts/ai_image_validator.py --test

# 3. If satisfied, run on all images
python scripts/ai_image_validator.py

# 4. Review the report
cat data/validation_reports/ai_validation_summary_*.txt

# 5. Fix invalid images and re-validate
python scripts/ai_image_validator.py --resume
```
