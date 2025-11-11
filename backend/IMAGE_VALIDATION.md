# Image Validation System

Comprehensive image validation system for UFC fighter photos using facial detection, quality analysis, and duplicate detection.

## Overview

This system validates fighter images stored in `data/images/fighters/` by:
- **Face Detection**: Using OpenCV Haar Cascades to detect human faces
- **Quality Analysis**: Measuring resolution, sharpness, brightness
- **Duplicate Detection**: Using perceptual hashing to find visually similar images
- **Validation Flags**: Automatic flagging of problematic images

## Architecture

### Components

1. **Database Schema** (`backend/db/models/__init__.py`)
   - New fields added to `Fighter` model:
     - `image_quality_score` - Overall quality 0-100
     - `image_resolution_width/height` - Image dimensions
     - `has_face_detected` - Boolean for face detection
     - `face_count` - Number of faces detected
     - `image_validation_flags` - JSON field with issue flags
     - `face_encoding` - Binary face encoding for duplicate detection
     - `image_validated_at` - Timestamp of validation

2. **Validator Service** (`backend/services/image_validator.py`)
   - `ImageValidator` class with methods:
     - `validate_image(fighter_id)` - Validate single image
     - `find_duplicates(fighter_hashes)` - Detect duplicate images
   - Uses OpenCV for face detection and quality metrics
   - Generates perceptual hashes for duplicate detection

3. **Validation Script** (`backend/scripts/validate_images.py`)
   - CLI command to process all images in batches
   - Stores validation results in database
   - Detects duplicates across all fighters

4. **API Endpoints** (`backend/api/image_validation.py`)
   - `GET /image-validation/stats` - Overall statistics
   - `GET /image-validation/low-quality` - Fighters with low quality images
   - `GET /image-validation/no-face` - Fighters without detected faces
   - `GET /image-validation/duplicates` - Potential duplicate images
   - `GET /image-validation/flags` - Filter by specific flag type
   - `GET /image-validation/{fighter_id}` - Validation details for fighter

## Usage

### Running Validation

```bash
# Validate all images (skips already validated)
make validate-images-facial

# Test on 10 images
make validate-images-facial-test

# Re-validate all images (including already validated)
make validate-images-facial-force

# Show statistics only
make validate-images-facial-stats
```

### Using the API

```bash
# Get validation statistics
curl http://localhost:8000/image-validation/stats

# Get fighters with low quality images (< 50 score)
curl "http://localhost:8000/image-validation/low-quality?min_score=50&limit=20"

# Get fighters without detected faces
curl http://localhost:8000/image-validation/no-face

# Get potential duplicate images
curl http://localhost:8000/image-validation/duplicates

# Get fighters with specific flag
curl "http://localhost:8000/image-validation/flags?flag=low_resolution"

# Get validation details for specific fighter
curl http://localhost:8000/image-validation/{fighter_id}
```

## Quality Metrics

### Quality Score (0-100)

The quality score is calculated from multiple factors:

- **Resolution (30 points)**:
  - ≥400px: 30 points
  - ≥300px: 25 points
  - ≥200px: 20 points
  - ≥150px: 10 points

- **Sharpness (30 points)**:
  - Blur score ≥500: 30 points
  - Blur score ≥300: 25 points
  - Blur score ≥100: 15 points
  - Otherwise: 5 points

- **Brightness (20 points)**:
  - 30-225 range: 20 points
  - Outside range: 10 points

- **Face Detection (20 points)**:
  - Face detected: 20 points
  - No face: 0 points

### Validation Flags

Images are automatically flagged for:

- `low_resolution` - Width or height < 150px
- `no_face_detected` - No human face found
- `multiple_faces` - More than one face detected
- `blurry_image` - Blur score < 100
- `too_dark` - Average brightness < 30
- `too_bright` - Average brightness > 225
- `potential_duplicates` - Perceptual hash matches other fighters

## Duplicate Detection

The system uses **perceptual hashing** (pHash) to detect visually similar images:

1. Resize image to 32x32
2. Apply Discrete Cosine Transform (DCT)
3. Extract low-frequency components (8x8)
4. Generate 64-bit hash based on median threshold
5. Compare hashes using Hamming distance

**Threshold**: Hamming distance ≤ 5 (out of 64 bits)

### Why Duplicates Matter

Duplicate images may indicate:
- Same fighter with multiple IDs
- Incorrectly assigned images
- Stock placeholder photos
- Data quality issues

## Face Detection

Uses **OpenCV Haar Cascade Classifier**:
- Pre-trained model for frontal face detection
- Fast and reliable for profile photos
- Detects faces in various lighting conditions
- Returns bounding boxes for detected faces

### Face Encoding

For detected faces:
- Extract face region from bounding box
- Resize to 64x64 grayscale
- Calculate histogram (256 bins)
- Normalize and serialize to bytes
- Store in database for similarity comparison

## Example Queries

### Find Fighters Needing Better Images

```sql
-- Low quality images (< 40 score)
SELECT name, image_quality_score, image_resolution_width, image_resolution_height
FROM fighters
WHERE image_quality_score < 40
ORDER BY image_quality_score ASC
LIMIT 20;

-- Images without faces
SELECT name, image_quality_score
FROM fighters
WHERE has_face_detected = FALSE
  AND image_validated_at IS NOT NULL
ORDER BY name;

-- Fighters with multiple issues
SELECT
  name,
  image_quality_score,
  has_face_detected,
  image_validation_flags
FROM fighters
WHERE jsonb_array_length(
  COALESCE(image_validation_flags::jsonb, '[]'::jsonb)
) > 2;
```

### Statistics Queries

```sql
-- Overall validation summary
SELECT
  COUNT(*) as total_fighters,
  COUNT(image_validated_at) as validated,
  COUNT(CASE WHEN has_face_detected THEN 1 END) as with_faces,
  AVG(image_quality_score) as avg_quality,
  COUNT(CASE WHEN image_quality_score < 50 THEN 1 END) as low_quality
FROM fighters;

-- Flag distribution
SELECT
  jsonb_object_keys(image_validation_flags) as flag_type,
  COUNT(*) as count
FROM fighters
WHERE image_validation_flags IS NOT NULL
GROUP BY flag_type
ORDER BY count DESC;
```

## Database Migration

The validation fields are added via Alembic migration:

```bash
# Apply migration
make db-upgrade

# Or manually
cd backend
../.venv/bin/python -m alembic upgrade head
```

Migration file: `backend/db/migrations/versions/b03ad5817fc9_add_image_validation_fields.py`

## Performance Considerations

### Batch Processing

The validation script processes fighters in batches:
- Default batch size: 100 fighters
- Commits to database after each batch
- Logs progress every 50 images

### Optimization Tips

1. **Run during off-peak hours**: Validation is CPU-intensive
2. **Use limit flag for testing**: `--limit 100` for quick tests
3. **Skip re-validation**: Default behavior skips already validated images
4. **Database indexes**: Automatically created on `has_face_detected` and `image_validated_at`

### Expected Performance

- **Validation speed**: ~5-10 images/second (depends on image size and CPU)
- **Total time for 4,212 images**: ~10-15 minutes
- **Duplicate detection**: O(n²) comparison, runs after all validations

## Troubleshooting

### OpenCV Haar Cascade Not Found

```bash
# Ensure OpenCV is installed with cascade files
pip install opencv-python

# Verify cascade path
python -c "import cv2; print(cv2.data.haarcascades)"
```

### Face Detection Not Working

- Ensure images are valid (not corrupted)
- Check image format (JPEG, PNG, WebP supported)
- Verify image has sufficient resolution (≥30px faces)
- Try adjusting `scaleFactor` parameter (default: 1.1)

### Slow Validation

- Reduce batch size: `--batch-size 50`
- Use limit flag for testing: `--limit 100`
- Check disk I/O performance
- Ensure database connection is fast

### Database Migration Issues

```bash
# Check current migration
cd backend && ../.venv/bin/python -m alembic current

# Show migration history
cd backend && ../.venv/bin/python -m alembic history

# Rollback migration
cd backend && ../.venv/bin/python -m alembic downgrade -1
```

## Future Enhancements

Potential improvements:

1. **Deep Learning Face Detection**:
   - Use dlib or MediaPipe for better accuracy
   - Face recognition for identity verification
   - Facial landmarks for quality assessment

2. **Advanced Quality Metrics**:
   - Color balance analysis
   - Aspect ratio validation
   - Background complexity score
   - Compression artifact detection

3. **Automatic Remediation**:
   - Auto-crop faces
   - Brightness adjustment
   - Resolution upscaling
   - Replace low-quality images

4. **Web Dashboard**:
   - Visual interface for reviewing flagged images
   - Side-by-side comparison for duplicates
   - Bulk actions (delete, replace, approve)
   - Export reports

5. **Continuous Monitoring**:
   - Validate new images on upload
   - Scheduled re-validation jobs
   - Quality score trending
   - Alerting for quality degradation

## API Response Examples

### GET /image-validation/stats

```json
{
  "total_fighters": 4212,
  "validated": 4212,
  "with_faces": 3845,
  "without_faces": 367,
  "low_quality": 128,
  "with_flags": 495,
  "flag_breakdown": {
    "low_resolution": 82,
    "no_face_detected": 367,
    "multiple_faces": 15,
    "blurry_image": 43,
    "too_dark": 28,
    "too_bright": 12,
    "potential_duplicates": 23
  }
}
```

### GET /image-validation/low-quality

```json
{
  "fighters": [
    {
      "fighter_id": "abc123",
      "name": "John Doe",
      "image_url": "images/fighters/abc123.jpg",
      "quality_score": 35.5,
      "resolution": "150x150",
      "has_face": true,
      "flags": {
        "low_resolution": {
          "width": 150,
          "height": 150,
          "threshold": "150x150"
        },
        "blurry_image": {
          "blur_score": 85.2,
          "threshold": 100.0
        }
      },
      "validated_at": "2025-11-11T00:45:23.123Z"
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0
}
```

### GET /image-validation/duplicates

```json
{
  "fighters": [
    {
      "fighter_id": "abc123",
      "name": "John Doe",
      "image_url": "images/fighters/abc123.jpg",
      "quality_score": 75.0,
      "duplicates": [
        {
          "fighter_id": "def456",
          "name": "John Smith"
        }
      ]
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0
}
```

## Contributing

When adding new validation metrics:

1. Add field to `Fighter` model in `backend/db/models/__init__.py`
2. Create Alembic migration
3. Update `ImageValidator` class in `backend/services/image_validator.py`
4. Add corresponding API endpoint in `backend/api/image_validation.py`
5. Update this documentation

## References

- [OpenCV Haar Cascades](https://docs.opencv.org/3.4/db/d28/tutorial_cascade_classifier.html)
- [Perceptual Hashing](https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html)
- [Image Quality Assessment](https://en.wikipedia.org/wiki/Image_quality)
- [Laplacian Blur Detection](https://www.pyimagesearch.com/2015/09/07/blur-detection-with-opencv/)
