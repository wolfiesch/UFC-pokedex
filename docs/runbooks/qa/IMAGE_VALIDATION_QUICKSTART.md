# Image Validation System - Quick Start

A comprehensive system to validate, analyze, and flag fighter images using facial detection and quality metrics.

## 🚀 Quick Start

### 1. Run Database Migration

```bash
# Apply the migration to add validation fields
make db-upgrade
```

### 2. Validate Images

```bash
# Test on 10 images first
make validate-images-facial-test

# Validate all images (~10-15 minutes for 4,212 images)
make validate-images-facial

# Show validation statistics
make validate-images-facial-stats
```

### 3. Query Results via API

```bash
# Get validation statistics
curl http://localhost:8000/image-validation/stats

# Get low-quality images
curl http://localhost:8000/image-validation/low-quality

# Get images without faces
curl http://localhost:8000/image-validation/no-face

# Get duplicate images
curl http://localhost:8000/image-validation/duplicates
```

## 📊 What It Detects

### Quality Metrics (0-100 score)
- ✅ **Resolution**: Width & height in pixels
- ✅ **Sharpness**: Blur detection using Laplacian variance
- ✅ **Brightness**: Average pixel intensity
- ✅ **Face Detection**: Detects human faces using OpenCV

### Validation Flags
- 🔴 **low_resolution**: Image < 150x150px
- 🔴 **no_face_detected**: No human face found
- 🔴 **multiple_faces**: More than one face detected
- 🔴 **blurry_image**: Blur score < 100
- 🔴 **too_dark**: Brightness < 30
- 🔴 **too_bright**: Brightness > 225
- 🔴 **potential_duplicates**: Perceptual hash matches another fighter

## 🎯 Use Cases

### Find Images Needing Replacement
```bash
# Low quality images (quality score < 40)
curl "http://localhost:8000/image-validation/low-quality?min_score=40&limit=50"
```

### Identify False Images
```bash
# Images without detected faces (may be action shots or placeholders)
curl http://localhost:8000/image-validation/no-face
```

### Detect Duplicate/Similar Images
```bash
# Find potential duplicates (same image used for different fighters)
curl http://localhost:8000/image-validation/duplicates
```

### Filter by Specific Issue
```bash
# Get all blurry images
curl "http://localhost:8000/image-validation/flags?flag=blurry_image"

# Get all low resolution images
curl "http://localhost:8000/image-validation/flags?flag=low_resolution"
```

## 📋 Available Commands

```bash
make validate-images-facial          # Validate all images
make validate-images-facial-test     # Test on 10 images
make validate-images-facial-stats    # Show statistics
make validate-images-facial-force    # Re-validate all (including validated)
```

## 🔧 Advanced Usage

### Manual Script Execution

```bash
# Run validation with custom options
cd backend
../.venv/bin/python -m scripts.validate_images --batch-size 100 --limit 500

# Show help
../.venv/bin/python -m scripts.validate_images --help
```

### Query Database Directly

```sql
-- Find fighters with low quality images
SELECT name, image_quality_score, has_face_detected
FROM fighters
WHERE image_quality_score < 50
ORDER BY image_quality_score ASC;

-- Count images by flag type
SELECT
  jsonb_object_keys(image_validation_flags) as flag,
  COUNT(*) as count
FROM fighters
WHERE image_validation_flags IS NOT NULL
GROUP BY flag
ORDER BY count DESC;
```

## 📈 Expected Results

Based on 4,212 fighter images:

- **Validation Time**: 10-15 minutes for full dataset
- **Expected Face Detection Rate**: ~85-90% (depending on image quality)
- **Typical Low Quality Count**: ~5-10% of images
- **Duplicate Detection**: ~1-2% of images

## 🆘 Troubleshooting

### OpenCV Not Found
```bash
# Reinstall opencv-python
uv pip install opencv-python
```

### Migration Issues
```bash
# Check current migration version
cd backend && ../.venv/bin/python -m alembic current

# Rollback if needed
cd backend && ../.venv/bin/python -m alembic downgrade -1
```

### API Endpoints Not Working
```bash
# Restart the backend
make api
```

## 📚 Full Documentation

See `backend/IMAGE_VALIDATION.md` for complete documentation including:
- Architecture details
- Quality score calculation
- Duplicate detection algorithm
- Database schema
- API reference
- Performance optimization

## 🎉 What's Next?

After validation:
1. Review flagged images via API endpoints
2. Replace low-quality images with better versions
3. Investigate duplicate images for data quality issues
4. Use validation flags to prioritize image improvements

---

**Current Date/Time**: 11/11/2025 12:43 AM
