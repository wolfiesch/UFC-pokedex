# Intelligent Fighter Image Face Cropping

**Created**: November 4, 2025
**Status**: Planning
**Priority**: High
**Complexity**: Medium-High

---

**IMPLEMENTATION STATUS**: ✅ COMPLETED (Core Implementation)

**Implemented Date**: 2025-11-04

**Implementation Summary**: Successfully implemented intelligent face detection and cropping system for fighter images. The system uses OpenCV and dlib for face detection, automatically crops images to focus on fighter faces, and stores cropped versions separately. **IMPORTANT**: Original images are preserved and continue to be used for all fighter cards. Cropped images are used exclusively for opponent images in the fight history graph to provide better visual focus on small avatars.

---

## Usage

### Processing Fighter Images

Run the batch processing script to detect faces and create cropped versions:

```bash
# Process all fighters with images
.venv/bin/python scripts/process_fighter_images.py --all

# Process specific fighters
.venv/bin/python scripts/process_fighter_images.py --fighter-ids abc123,def456

# Dry-run mode (detect only, no cropping)
.venv/bin/python scripts/process_fighter_images.py --all --dry-run

# Set concurrency (default: 4 workers)
.venv/bin/python scripts/process_fighter_images.py --all --workers 8

# Force reprocess already cropped images
.venv/bin/python scripts/process_fighter_images.py --all --force
```

### How It Works

1. **Face Detection**: Uses dlib's HOG detector (fast) with CNN fallback (accurate)
2. **Intelligent Cropping**: Adds smart padding around detected faces (head room, shoulders)
3. **Quality Control**: Validates crops based on face size, position, and sharpness
4. **Non-Destructive**: Original images remain untouched in `data/images/fighters/`
5. **Cropped Storage**: Face-cropped versions saved to `data/images/fighters/cropped/`
6. **Database Tracking**: Stores `cropped_image_url`, `face_detection_confidence`, and `crop_processed_at`

### Image Usage Strategy

**IMPORTANT DISTINCTION**:
- **Original images**: Used for all fighter cards, detail pages, and main UI elements
- **Cropped images**: Used ONLY for opponent avatars in the fight history graph (where small, focused portraits work better)

This dual-image approach ensures:
- Fighter cards retain their full original images (often full-body or action shots)
- Small opponent avatars in graphs show clear, focused faces
- No visual inconsistency between main cards and opponent thumbnails

## What Was Implemented

### Core Services
1. **Face Detection Service** (`backend/services/face_detection.py`)
   - dlib HOG detector for fast face detection
   - Automatic CNN fallback for difficult angles
   - Multi-face handling (selects largest/most prominent face)
   - Confidence scoring based on size, position, and aspect ratio

2. **Image Cropper Service** (`backend/services/image_cropper.py`)
   - Intelligent crop box calculation with smart padding
   - Square aspect ratio (512x512) for consistency
   - Quality validation (face size, sharpness checks)
   - Non-destructive processing (preserves originals)

3. **Batch Processing Script** (`scripts/process_fighter_images.py`)
   - CLI tool for processing fighter images
   - Parallel processing with configurable workers
   - Progress tracking with rich console output
   - Statistics reporting (success rate, confidence distribution)
   - Database metadata updates

### Database Schema
- Added to `fighters` table:
  - `cropped_image_url` (String, nullable) - Path to cropped version
  - `face_detection_confidence` (Float, nullable) - Detection quality score
  - `crop_processed_at` (DateTime, nullable) - Processing timestamp
- Migration: `8a8176360005_add_cropped_image_fields.py`

### Image Resolution
- Updated `backend/services/image_resolver.py`:
  - New `resolve_fighter_image_cropped()` function
  - Prioritizes: DB cropped path → filesystem cropped → original image
  - Separate from `resolve_fighter_image()` which always returns originals

- Updated `backend/db/repositories.py`:
  - Fight graph nodes now use `resolve_fighter_image_cropped()` for opponent images
  - Regular fighter queries continue using `resolve_fighter_image()` for original images

### Dependencies Added
- `opencv-python>=4.8.1` - Image processing and manipulation
- `dlib>=19.24.2` - Face detection models
- `numpy>=1.26.0` - Array operations
- `pillow>=10.1.0` - Additional image I/O support

## Testing

### Manual Testing Steps
1. Start the backend: `make api`
2. Run batch processing on a few fighters:
   ```bash
   .venv/bin/python scripts/process_fighter_images.py --limit 10 --all
   ```
3. Check output in `data/images/fighters/cropped/`
4. Verify database updated with cropped URLs:
   ```sql
   SELECT id, name, cropped_image_url, face_detection_confidence
   FROM fighters
   WHERE cropped_image_url IS NOT NULL
   LIMIT 5;
   ```
5. View in UI: Navigate to a fighter's detail page and check the fight history graph

### Expected Behavior
- **High confidence crops** (>0.8): Clear frontal faces, well-centered
- **Low confidence crops** (0.5-0.8): Profile shots, partially occluded faces
- **Failed detections**: Original image used as fallback
- **Processing time**: ~1-2 seconds per image (depends on image size and CPU)

## Deviations from Original Plan

1. **Testing**: Unit tests not implemented in this iteration (focused on core functionality)
2. **Test Fixtures**: Sample test images not created (can be added later)
3. **CNN Model**: CNN detector support added but model file not downloaded (optional enhancement)
4. **Image Usage**: Clarified that cropped images are for opponents ONLY, not fighter cards

## Known Limitations

1. **CNN Model**: Requires manual download of `mmod_human_face_detector.dat` for improved accuracy on angled faces
2. **Performance**: Processing 4,000+ images may take 1-2 hours (parallelization helps)
3. **Quality Variance**: Some fighters may have low-quality source images that don't crop well
4. **Manual Review**: May need manual curation for edge cases (multiple faces, masked fighters)

## Next Steps (Future Enhancements)

1. **Testing Suite**: Add unit and integration tests
2. **CNN Model Integration**: Download and integrate CNN detector for better accuracy
3. **Frontend Integration**: Add UI indicators for cropped vs original images
4. **Quality Dashboard**: Build admin interface to review and approve crops
5. **Automated Re-cropping**: Trigger when new fighter images are scraped
6. **ML Improvements**: Train custom model to identify "main subject" in group photos

---

## Original Plan Content (Preserved Below)

---

## Overview

Replace the current initials-based placeholder system (`FighterImagePlaceholder`) with intelligent face detection and cropping for fighter images. The system should automatically detect faces in scraped fighter images and crop them intelligently to create consistent, professional-looking portraits for the fighter cards and detail pages.

## Current State Analysis

### Existing Components
- **Frontend**:
  - `FighterImagePlaceholder.tsx` - Displays colored circles with fighter initials when no image is available
  - `FighterCard.tsx` - Uses image fallback to placeholder when `image_url` is missing or errors
  - `FighterImageFrame.tsx` - Provides consistent framing for fighter images
  - Image resolution via `resolveImageUrl()` utility

- **Backend**:
  - `Fighter` model - Has `image_url` (String, nullable) and `image_scraped_at` (DateTime, nullable) fields
  - `image_resolver.py` - Resolves fighter images from filesystem cache (`data/images/fighters/`)
  - Image scrapers: `sherdog_images.py`, `wikimedia_image_scraper.py`, `smart_image_finder.py`
  - Image processing scripts: `normalize_fighter_images.py`, `detect_placeholder_images.py`

### Current Image Storage
- Location: `data/images/fighters/`
- Format: `{fighter_id}.{jpg|jpeg|png|webp}`
- ~4,216 images currently stored
- No face detection or cropping applied

### Current Limitations
1. Images are not cropped - full body shots, wide angle photos
2. Inconsistent framing across different fighter images
3. Faces may be small or off-center in the frame
4. No automated quality control for face visibility
5. Initials placeholder used when images fail to load

## Goals and Requirements

### Primary Goals
1. Automatically detect faces in fighter images
2. Intelligently crop images to center on the fighter's face
3. Maintain consistent aspect ratio and dimensions
4. Create professional-looking portrait crops
5. Preserve original images (non-destructive processing)
6. Handle edge cases gracefully (multiple faces, no faces, occluded faces)

### Success Criteria
- ✅ Face detection accuracy > 95% on fighter images
- ✅ Cropped images consistently frame the face within the upper 60% of the image
- ✅ Processing time < 2 seconds per image (batch mode)
- ✅ Fallback to original image when face detection fails
- ✅ Zero data loss - original images preserved
- ✅ Support for offline processing (no external API dependencies)
- ✅ Seamless integration with existing image resolution flow

## Technical Approach

### Architecture Choice: OpenCV + dlib

**Rationale**:
- **OpenCV**: Industry-standard computer vision library, well-documented, fast
- **dlib**: Excellent face detection accuracy with pre-trained models
- **No external APIs**: Keep processing local, avoid rate limits and costs
- **Python ecosystem**: Integrates seamlessly with existing backend

**Alternatives Considered**:
- **MediaPipe (Google)**: More modern but heavier dependency
- **face_recognition library**: Built on dlib, simpler API but less control
- **Cloud APIs (AWS Rekognition, Google Vision)**: Cost concerns, network dependency
- **MTCNN**: Good accuracy but slower than dlib

### Processing Pipeline

```
Original Image (data/images/fighters/{id}.jpg)
    ↓
Face Detection (dlib HOG or CNN detector)
    ↓
Bounding Box Calculation + Intelligent Padding
    ↓
Crop with Smart Margins (head room, shoulders visible)
    ↓
Resize to Standard Dimensions (512x512 target)
    ↓
Save Cropped Version (data/images/fighters/cropped/{id}.jpg)
    ↓
Update Database (cropped_image_url field)
```

### Face Detection Strategy

**Primary Method**: dlib HOG (Histogram of Oriented Gradients) detector
- Fast (CPU-friendly)
- Accurate for frontal faces
- Works well on UFC fighter promotional photos

**Fallback Method**: dlib CNN detector (if HOG fails)
- More accurate for profile shots, angled faces
- Slower, requires more CPU
- Use only when HOG returns no faces

**Multi-face Handling**:
1. If multiple faces detected → select largest face (likely the fighter)
2. If confidence scores available → select highest confidence face
3. Log warning for manual review

### Intelligent Cropping Algorithm

**Bounding Box Expansion**:
```python
# Starting from face bounding box (x, y, w, h)
padding_top = h * 0.4      # Head room above face
padding_sides = w * 0.3    # Space on left/right
padding_bottom = h * 0.6   # Include shoulders/upper torso

# Target aspect ratio: 1:1 (square) for consistency
# Face should occupy ~40-50% of crop height
```

**Edge Case Handling**:
- **Face too close to edge**: Shift crop box to keep face centered
- **Image too small**: Pad with background blur or skip cropping
- **No face detected**: Keep original image, log for manual review
- **Occluded face (mask, hand)**: Attempt crop, flag for review if confidence < threshold

### Image Quality Control

**Pre-processing Checks**:
1. Minimum resolution: 200x200 pixels
2. File format validation (JPEG, PNG, WebP)
3. Corruption detection (verify image loads)

**Post-processing Validation**:
1. Face occupies 35-55% of crop height
2. Face center is within middle 40% of image width
3. No excessive cropping (< 80% of original discarded)
4. Sharpness check (detect blurry crops)

## Implementation Plan

### Phase 1: Foundation Setup
**Files to Create**:
- `backend/services/face_detection.py` - Core face detection service
- `backend/services/image_cropper.py` - Intelligent cropping logic
- `scripts/process_fighter_images.py` - Batch processing script
- `tests/backend/test_face_detection.py` - Unit tests

**Files to Modify**:
- `backend/db/models/__init__.py` - Add `cropped_image_url` field to Fighter model
- `backend/services/image_resolver.py` - Prioritize cropped images
- `pyproject.toml` - Add dependencies (opencv-python, dlib, numpy)

**Dependencies to Add**:
```toml
opencv-python = "^4.8.1"
dlib = "^19.24.2"
numpy = "^1.26.0"
pillow = "^10.1.0"  # Already present, verify version
```

**Database Migration**:
```python
# New migration: add_cropped_image_url
def upgrade():
    op.add_column('fighters',
        sa.Column('cropped_image_url', sa.String(), nullable=True))
    op.add_column('fighters',
        sa.Column('face_detection_confidence', sa.Float(), nullable=True))
    op.add_column('fighters',
        sa.Column('crop_processed_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('fighters', 'crop_processed_at')
    op.drop_column('fighters', 'face_detection_confidence')
    op.drop_column('fighters', 'cropped_image_url')
```

### Phase 2: Core Implementation

#### Task 2.1: Face Detection Service
**File**: `backend/services/face_detection.py`

**Key Functions**:
```python
class FaceDetectionService:
    def __init__(self):
        # Load dlib models (download on first run)
        self.hog_detector = dlib.get_frontal_face_detector()
        self.cnn_detector = None  # Lazy load if needed

    def detect_faces(self, image_path: str) -> list[FaceBox]:
        """Detect all faces in image, return bounding boxes."""
        pass

    def get_primary_face(self, faces: list[FaceBox]) -> FaceBox | None:
        """Select the most likely fighter face from multiple detections."""
        pass

    def calculate_confidence(self, face: FaceBox, image: np.ndarray) -> float:
        """Estimate detection confidence based on size, position, clarity."""
        pass
```

**Error Handling**:
- Graceful degradation if dlib models fail to load
- Timeout protection for large images (max 10s per image)
- Memory management for batch processing

#### Task 2.2: Intelligent Cropping Service
**File**: `backend/services/image_cropper.py`

**Key Functions**:
```python
class ImageCropper:
    def __init__(self, target_size: tuple[int, int] = (512, 512)):
        self.target_size = target_size
        self.face_detector = FaceDetectionService()

    def crop_to_face(self, image_path: str, output_path: str) -> CropResult:
        """Main entry point - detect face and create intelligent crop."""
        pass

    def calculate_crop_box(self, face_box: FaceBox, image_dims: tuple) -> CropBox:
        """Calculate optimal crop box with smart padding."""
        pass

    def apply_crop(self, image: np.ndarray, crop_box: CropBox) -> np.ndarray:
        """Execute crop with edge case handling."""
        pass

    def validate_crop_quality(self, cropped: np.ndarray, face_box: FaceBox) -> bool:
        """Quality gate - ensure crop meets standards."""
        pass
```

**Quality Metrics**:
```python
@dataclass
class CropResult:
    success: bool
    cropped_path: str | None
    confidence: float
    face_area_percent: float  # Face size relative to crop
    quality_score: float  # 0-1, composite quality metric
    fallback_to_original: bool
    error_message: str | None
```

#### Task 2.3: Batch Processing Script
**File**: `scripts/process_fighter_images.py`

**Features**:
- Process all fighters or specific fighter IDs
- Parallel processing (ThreadPoolExecutor, default 4 workers)
- Progress tracking with rich/tqdm
- Automatic resume from failures
- Detailed logging and statistics

**CLI Interface**:
```bash
# Process all fighters
.venv/bin/python scripts/process_fighter_images.py --all

# Process specific fighters
.venv/bin/python scripts/process_fighter_images.py --fighter-ids abc123,def456

# Dry-run mode (detect only, no cropping)
.venv/bin/python scripts/process_fighter_images.py --all --dry-run

# Set concurrency
.venv/bin/python scripts/process_fighter_images.py --all --workers 8

# Force reprocess already cropped images
.venv/bin/python scripts/process_fighter_images.py --all --force
```

**Statistics to Track**:
- Total images processed
- Successful crops with high confidence (>0.8)
- Successful crops with low confidence (0.5-0.8)
- Failed detections (fallback to original)
- Processing time (avg, min, max)
- Disk space saved/used

### Phase 3: Integration

#### Task 3.1: Update Image Resolution
**File**: `backend/services/image_resolver.py`

**Changes**:
```python
def resolve_fighter_image(fighter_id: str, stored_path: str | None, cropped_path: str | None) -> str | None:
    """Priority: cropped_path > stored_path > filesystem fallback."""

    # NEW: Prefer cropped version
    if cropped_path:
        return cropped_path

    # Existing logic...
    if stored_path:
        return stored_path

    # NEW: Check for cropped in filesystem
    cropped = _find_local_image(fighter_id, prefix="cropped")
    if cropped:
        return cropped

    return _find_local_image(fighter_id)
```

#### Task 3.2: Update Repository Layer
**File**: `backend/db/repositories.py`

**Changes**:
- Include `cropped_image_url` in fighter queries
- Pass to `resolve_fighter_image()` service
- Update fighter serialization to include cropped URL

#### Task 3.3: Frontend Optimization (Optional)
**File**: `frontend/src/components/FighterCard.tsx`

**Potential Improvements**:
- Progressive loading: Show blurred placeholder → full image
- Lazy loading with intersection observer
- Image optimization with Next.js `<Image>` component
- Preload cropped images for better UX

**Note**: This phase is optional since the backend changes are transparent to the frontend. The existing image resolution flow will automatically serve cropped images.

### Phase 4: Testing & Validation

#### Unit Tests
**File**: `tests/backend/test_face_detection.py`

**Test Cases**:
```python
def test_detect_single_face_frontal()
def test_detect_multiple_faces_select_largest()
def test_no_face_detected_returns_none()
def test_profile_face_detection()
def test_occluded_face_low_confidence()
def test_calculate_crop_box_with_padding()
def test_edge_case_face_at_image_boundary()
def test_crop_quality_validation_passes()
def test_crop_quality_validation_fails()
```

**Test Images Required**:
- Create `tests/fixtures/images/` with sample fighter photos:
  - `frontal_face.jpg` - Clear frontal shot
  - `profile_face.jpg` - Side profile
  - `multiple_faces.jpg` - Fighter + coach/corner
  - `no_face.jpg` - Logo or venue shot
  - `low_quality.jpg` - Blurry/pixelated image
  - `edge_case.jpg` - Face at border

#### Integration Tests
**File**: `tests/backend/test_image_processing_integration.py`

**Test Workflow**:
1. Start with original fighter image
2. Run face detection
3. Apply cropping
4. Validate output file exists
5. Check database updated correctly
6. Verify image_resolver returns cropped version

#### Manual QA Checklist
- [ ] Process 100 random fighters, visually inspect crops
- [ ] Verify no crashes on corrupted images
- [ ] Test with minimal images (200x200)
- [ ] Test with huge images (4000x3000+)
- [ ] Verify graceful fallback when dlib models missing
- [ ] Check memory usage during batch processing
- [ ] Validate cropped images display correctly in UI

### Phase 5: Deployment & Monitoring

#### Pre-deployment Steps
1. Run migration: `make db-upgrade`
2. Install new dependencies: `uv sync`
3. Download dlib models (automatic on first run)
4. Process sample batch (100 fighters) to verify

#### Batch Processing Strategy
**Option A: One-time bulk process**
```bash
# Process all existing fighters overnight
nohup .venv/bin/python scripts/process_fighter_images.py --all --workers 8 > crop_log.txt 2>&1 &
```

**Option B: Incremental processing**
```bash
# Add to cron: process 500 fighters per hour
0 * * * * cd /path/to/project && .venv/bin/python scripts/process_fighter_images.py --limit 500 --skip-processed
```

#### Monitoring Metrics
- Track crop success rate (target: >95%)
- Monitor processing time trends
- Alert on high failure rates (>10%)
- Log face detection confidence distribution
- Track disk space usage for cropped images

#### Rollback Plan
If cropping causes issues:
1. Update `image_resolver.py` to ignore `cropped_image_url`
2. No data loss - original images preserved
3. Can reprocess with adjusted parameters

## Files Summary

### Files to Create (8 new files)
1. `backend/services/face_detection.py` - Face detection service
2. `backend/services/image_cropper.py` - Cropping logic
3. `scripts/process_fighter_images.py` - Batch processing CLI
4. `backend/db/migrations/versions/XXXXX_add_cropped_image_fields.py` - Migration
5. `tests/backend/test_face_detection.py` - Unit tests
6. `tests/backend/test_image_processing_integration.py` - Integration tests
7. `tests/fixtures/images/` - Test image fixtures directory
8. `docs/guides/IMAGE_PROCESSING.md` - Documentation

### Files to Modify (4 files)
1. `backend/db/models/__init__.py` - Add cropped image fields
2. `backend/services/image_resolver.py` - Prioritize cropped images
3. `backend/db/repositories.py` - Include cropped URL in queries
4. `pyproject.toml` - Add opencv-python, dlib dependencies

### Files to Review (Reference only)
1. `scripts/normalize_fighter_images.py` - Existing normalization patterns
2. `scripts/detect_placeholder_images.py` - Placeholder detection logic
3. `frontend/src/components/FighterImagePlaceholder.tsx` - Current placeholder UI

## Dependencies and Prerequisites

### Python Libraries
```toml
[tool.uv.sources]
opencv-python = "^4.8.1"        # Computer vision operations
dlib = "^19.24.2"               # Face detection models
numpy = "^1.26.0"               # Array operations
pillow = "^10.1.0"              # Image I/O (verify existing)
```

### System Requirements
- **RAM**: 4GB minimum (8GB recommended for batch processing)
- **CPU**: Multi-core beneficial for parallel processing
- **Disk**: ~50-100MB additional for cropped images (assuming ~25KB per crop)
- **OS**: dlib compiles on Linux/macOS/Windows (may need cmake on some platforms)

### Pre-installation Notes
**dlib installation**:
```bash
# macOS (may need Xcode command line tools)
brew install cmake
uv sync  # Will compile dlib

# Linux (Ubuntu/Debian)
sudo apt-get install cmake libopenblas-dev liblapack-dev
uv sync

# Windows (requires Visual Studio Build Tools)
# Download from: https://visualstudio.microsoft.com/downloads/
uv sync
```

**Model Downloads**:
- dlib's HOG detector is built-in (no download needed)
- CNN detector (optional): Auto-downloaded on first use (~100MB)

## Potential Challenges and Edge Cases

### Challenge 1: Multiple Faces in Image
**Scenario**: Fighter photo includes coach, referee, or opponent

**Solution**:
- Select largest face (by bounding box area)
- If multiple faces similar size → highest confidence
- Log warning for manual review queue
- Future: ML classifier to identify "main subject"

### Challenge 2: Profile Shots / Non-Frontal Angles
**Scenario**: Fighter photographed from side, 3/4 angle

**Solution**:
- CNN detector handles angles better than HOG
- Automatically fallback to CNN if HOG fails
- Accept lower confidence threshold for profile shots (0.6 vs 0.8)
- May need manual curation for extreme angles

### Challenge 3: No Face Detected
**Scenario**: Logo images, full-body shots, masked fighters, corrupt files

**Solution**:
- Fallback to original image (no cropping)
- Log fighter ID for manual review
- Set `face_detection_confidence = 0.0` in DB
- Don't delete or hide original image

### Challenge 4: Occluded Faces (Hands, Gloves, Mask)
**Scenario**: Fighter covering face, wearing mask/helmet

**Solution**:
- dlib should still detect partial faces
- Lower confidence score will flag for review
- Accept crop if confidence > 0.5
- Manual curation queue for confidence 0.5-0.7 range

### Challenge 5: Low-Quality Source Images
**Scenario**: Blurry, pixelated, or very small images

**Solution**:
- Pre-filter images < 200x200 pixels
- Skip cropping if source quality too low
- Post-process sharpness check (Laplacian variance)
- Flag low-quality crops for re-scraping

### Challenge 6: Performance / Memory Issues
**Scenario**: Processing 4,000+ images crashes or is too slow

**Solution**:
- Batch processing with chunking (process 100 at a time)
- ThreadPoolExecutor with worker limit (default 4)
- Memory cleanup after each batch
- Progress checkpointing (resume from failures)
- Option to process incrementally via cron

### Challenge 7: Inconsistent Aspect Ratios
**Scenario**: Cropped images vary in dimensions

**Solution**:
- Force standard output size: 512x512 square
- Maintain face position consistency (center, upper 40%)
- Padding strategy: extend background vs. letterboxing
- Consider slight zoom vs. excessive padding

### Challenge 8: dlib Compilation Failures
**Scenario**: dlib doesn't compile on user's system

**Solution**:
- Provide pre-built wheels for common platforms
- Fallback: Use simpler OpenCV Haar Cascades (lower accuracy)
- Docker image with pre-installed dependencies
- Detailed installation docs with platform-specific steps

## Testing Strategy

### Unit Testing Approach
**Coverage Goals**:
- Face detection: 90%+ code coverage
- Cropping logic: 90%+ code coverage
- Edge case handlers: 100% coverage

**Mocking Strategy**:
- Mock dlib detectors for speed (use fixtures)
- Mock file I/O for isolation
- Real integration tests with sample images

### Integration Testing
**End-to-End Flow**:
```python
def test_full_image_processing_pipeline():
    # Given: Fighter with original image
    fighter = create_test_fighter(image_url="images/fighters/test123.jpg")

    # When: Process image
    result = ImageCropper().crop_to_face(
        "data/images/fighters/test123.jpg",
        "data/images/fighters/cropped/test123.jpg"
    )

    # Then: Cropped image exists and DB updated
    assert result.success
    assert Path("data/images/fighters/cropped/test123.jpg").exists()
    assert fighter.cropped_image_url == "images/fighters/cropped/test123.jpg"
    assert fighter.face_detection_confidence > 0.7
```

### Manual QA Process
1. **Sample Review**: Manually inspect 100 random crops
2. **Edge Case Testing**: Test known difficult images
3. **Performance Testing**: Measure batch processing time
4. **Memory Profiling**: Check memory usage over time
5. **Failure Analysis**: Review and categorize all failures

### Acceptance Criteria Validation
- [ ] 95%+ face detection success rate on test set
- [ ] Cropped faces within upper 60% of image (measured)
- [ ] Processing speed < 2s per image (average)
- [ ] Zero original image data loss
- [ ] Fallback works seamlessly (no broken images)
- [ ] Batch processing completes without crashes
- [ ] UI displays cropped images correctly

## Success Metrics

### Quantitative Metrics
| Metric | Target | Measurement |
|--------|--------|-------------|
| Face detection success rate | > 95% | Faces detected / Total images |
| Crop quality score | > 0.8 (avg) | Composite quality metric |
| Processing speed | < 2s/image | Average batch processing time |
| Face position accuracy | 90% in upper 60% | Automated position check |
| Fallback rate | < 10% | Images using original vs cropped |
| Memory usage | < 2GB peak | Process monitoring during batch |
| Disk space overhead | < 150MB | Total cropped image size |

### Qualitative Metrics
- **Visual Consistency**: Cropped images should have uniform framing
- **Professional Appearance**: Crops should look intentional, not arbitrary
- **User Experience**: No broken images, smooth loading
- **Maintainability**: Code is readable and well-documented

### Validation Process
1. Run batch processing on all 4,216 existing images
2. Generate statistics report (success rate, avg confidence, etc.)
3. Randomly sample 100 crops for manual inspection
4. User testing: Show before/after to 3-5 users for feedback
5. Performance benchmarking on production-like dataset

## Future Enhancements (Out of Scope)

### Phase 2 Improvements
1. **ML-based subject detection**: Train classifier to identify "fighter" vs "other people"
2. **Auto-rotation correction**: Detect and fix tilted images
3. **Background removal**: Isolate fighter from background for cleaner crops
4. **Dynamic crop aspect ratios**: Optimize for different UI contexts (card vs detail page)
5. **Real-time processing**: Crop images during scrape (not batch)

### Advanced Features
1. **Face landmark detection**: Align eyes horizontally for consistency
2. **Pose estimation**: Prefer action shots over static poses
3. **Quality enhancement**: Auto-sharpen, color correction, noise reduction
4. **A/B testing**: Test different crop strategies with user engagement metrics
5. **Crowd-sourced curation**: Let users flag bad crops for review

## Documentation Requirements

### Developer Documentation
**File**: `docs/guides/IMAGE_PROCESSING.md`

**Contents**:
- Architecture overview (with diagrams)
- How to run batch processing
- Adding new face detection algorithms
- Troubleshooting common issues
- Performance tuning guide

### User Documentation (Internal)
**File**: `docs/guides/IMAGE_CROPPING_OPERATIONS.md`

**Contents**:
- How to reprocess specific fighters
- Interpreting quality scores and confidence
- Manual review workflow
- Rollback procedures

### API Documentation
- Update OpenAPI schema for new cropped_image_url field
- Document image resolution priority order
- Add examples to schema descriptions

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Foundation | Setup, dependencies, migration | 3-4 hours |
| Phase 2: Core Implementation | Face detection + cropping services | 6-8 hours |
| Phase 3: Integration | Update resolvers, repositories | 2-3 hours |
| Phase 4: Testing | Unit + integration + manual QA | 4-6 hours |
| Phase 5: Deployment | Batch processing, monitoring | 2-3 hours |
| **Total** | | **17-24 hours** |

**Buffer**: Add 20% for unexpected issues = **20-29 hours total**

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| dlib installation issues | Medium | High | Provide Docker image, pre-built wheels |
| Low face detection accuracy | Low | Medium | Use CNN fallback, manual review queue |
| Performance bottlenecks | Medium | Medium | Parallel processing, chunking |
| Memory crashes on batch | Low | Medium | Process in smaller batches, cleanup |
| Inconsistent crop quality | Medium | Medium | Quality validation gates, tune parameters |
| Corrupt source images | Low | Low | Pre-validation, error handling |

## Conclusion

This plan provides a comprehensive roadmap for implementing intelligent face cropping for fighter images. The approach balances accuracy, performance, and maintainability while providing robust fallbacks for edge cases. The system is designed to be:

- **Non-destructive**: Original images are never modified
- **Fault-tolerant**: Graceful degradation on failures
- **Performant**: Batch processing optimized for thousands of images
- **Maintainable**: Clear separation of concerns, well-tested
- **Scalable**: Easily extended with ML improvements

By following this plan, we can replace the current initials-based placeholder system with professional, consistently-cropped fighter portraits that enhance the overall user experience of the UFC Pokedex.
