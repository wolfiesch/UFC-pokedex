# AI Image Validator - Quick Start

## 🚀 One-Line Commands (Copy & Paste)

### Method 1: Using Environment Variable (Recommended)

```bash
# Set your API key once
export OPENAI_API_KEY="YOUR_API_KEY_HERE"

# Then run any command without --api-key flag:
.venv/bin/python scripts/ai_image_validator.py --test
```

### Method 2: Using Command Line Flag

```bash
# Test on Muhammad Naimov's problematic image
.venv/bin/python scripts/ai_image_validator.py --api-key "YOUR_API_KEY_HERE" --fighter-ids "8d11d9c13e2ccdf7"

# Test mode (first 10 images)
.venv/bin/python scripts/ai_image_validator.py --api-key "YOUR_API_KEY_HERE" --test

# Validate ALL 4,633 images (~$0.21)
.venv/bin/python scripts/ai_image_validator.py --api-key "YOUR_API_KEY_HERE"
```

### Method 3: Using Test Script (Easiest)

```bash
# 1. Edit the file and add your API key
nano scripts/test_ai_validator.sh  # Change YOUR_API_KEY_HERE

# 2. Run the test
./scripts/test_ai_validator.sh
```

---

## 📋 Command Reference

| Command | Description | Cost |
|---------|-------------|------|
| `--fighter-ids "ID1,ID2"` | Validate specific fighters | ~$0.00005 per image |
| `--test` | Test mode (first 10 only) | ~$0.0005 |
| `--resume` | Resume interrupted run | Variable |
| `--batch-size N` | Process N images concurrently | No extra cost |
| `--api-key "KEY"` | Provide API key directly | N/A |

---

## 🔍 What Gets Detected?

The AI validator catches issues that traditional validation misses:

✅ **Illustrations/Paintings** (like Muhammad Naimov's historical painting)
✅ **Cartoons & Drawings**
✅ **Stock Photo Watermarks** (Alamy, Getty, Shutterstock)
✅ **Wrong Subjects** (not actual fighters)
✅ **Multiple People** in frame
✅ **Non-Professional Settings**

---

## 📊 Output

Reports are saved to `data/validation_reports/`:

- **JSON Report:** `ai_validation_report_TIMESTAMP.json`
- **Text Summary:** `ai_validation_summary_TIMESTAMP.txt`

Example invalid image output:
```
Fighter: Muhammad Naimov (ID: 8d11d9c13e2ccdf7)
Confidence: 100%
Reason: Historical illustration, not a photograph
Issues: painting, not_real_photo
Path: data/images/fighters/8d11d9c13e2ccdf7.jpg
```

---

## 🆘 Troubleshooting

### "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="sk-proj-..."
```

### "API key test failed"
- Check you have credits: https://platform.openai.com/account/billing
- Verify key starts with `sk-proj-` or `sk-`
- Try regenerating the key

### "Rate limit exceeded"
```bash
# Reduce batch size
.venv/bin/python scripts/ai_image_validator.py --batch-size 5
```

### Script interrupted?
```bash
# Resume where you left off
.venv/bin/python scripts/ai_image_validator.py --resume
```

---

## 💡 Pro Tips

1. **Start with test mode** to verify everything works before running on all images
2. **Use --resume** if your connection drops - it picks up where it left off
3. **Check the summary.txt file** first - it's easier to read than the JSON
4. **Total cost is ~$0.21** for all 4,633 images - very affordable!

---

## 📝 Example Workflow

```bash
# 1. Set API key
export OPENAI_API_KEY="sk-proj-abc123..."

# 2. Test on Muhammad Naimov's bad image
.venv/bin/python scripts/ai_image_validator.py --fighter-ids "8d11d9c13e2ccdf7"

# 3. Run test mode (10 images)
.venv/bin/python scripts/ai_image_validator.py --test

# 4. If satisfied, run full validation
.venv/bin/python scripts/ai_image_validator.py

# 5. Check the report
cat data/validation_reports/ai_validation_summary_*.txt | head -50
```

---

**Get your API key:** https://platform.openai.com/api-keys
**Add billing:** https://platform.openai.com/account/billing (add $5-10)
