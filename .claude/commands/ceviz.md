---
description: Run ceviz performance analysis with automatic report archiving and progress tracking
---

Run a ceviz performance analysis on the frontend with automatic backup of previous reports.

Please follow these steps:

1. **Check if backend is running** at http://localhost:8000/health
   - If not running, inform the user to start it with `make api` or `make dev-local`

2. **Create archive directory** if it doesn't exist:
   - Directory: `frontend/benchmarks/reports/`

3. **Backup existing report** (if it exists):
   - Check for `frontend/ceviz-report.html`
   - If exists, copy to `frontend/benchmarks/reports/ceviz-report-TIMESTAMP.html`
   - Use format: `YYYYMMDD_HHMMSS` for timestamp
   - Report the backup location

4. **Run ceviz analysis**:
   - Change to frontend directory
   - Run: `npx ceviz analyze --html ceviz-report.html .`
   - Also create timestamped version: `npx ceviz analyze --html benchmarks/reports/ceviz-report-TIMESTAMP.html .`

5. **Extract key metrics** from the new report:
   - Files analyzed
   - Total issues
   - Performance score
   - Analysis time

6. **Compare with previous report** (if backup exists):
   - Show difference in files analyzed
   - Show difference in total issues
   - Indicate if it's an improvement or regression

7. **Update progress document**:
   - Update or create `frontend/benchmarks/PROGRESS.md`
   - Add the new results with timestamp
   - Include comparison with previous run
   - List any notable changes

8. **Open the report** in browser:
   - Run: `open frontend/ceviz-report.html`

9. **Provide summary** including:
   - Current performance metrics
   - Comparison with previous run (improvement/regression)
   - Location of archived reports
   - Recommendation for next steps

**Note**: This command assumes you're running from the project root directory.
