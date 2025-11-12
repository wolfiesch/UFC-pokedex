# Custom Slash Commands

This directory contains custom slash commands for Claude Code to streamline common workflows.

## Available Commands

### `/ceviz`
Run ceviz performance analysis with automatic report archiving and progress tracking.

**What it does:**
- Automatically backs up previous report with timestamp
- Runs ceviz analysis on the frontend
- Extracts and compares key metrics
- Updates progress tracking document
- Opens report in browser
- Provides improvement/regression analysis

**Usage:**
```
/ceviz
```

**Prerequisites:**
- Backend must be running (start with `make api` or `make dev-local`)
- Must be run from project root directory

**Output locations:**
- Current report: `frontend/ceviz-report.html`
- Archived reports: `frontend/benchmarks/reports/ceviz-report-YYYYMMDD_HHMMSS.html`
- Progress tracking: `frontend/benchmarks/PROGRESS.md`

### `/newplan`
Create a new feature plan document in the `docs/plans/` directory.

**Usage:**
```
/newplan <feature description>
```

### `/runplan`
Implement a feature plan from the `docs/plans/` directory and update status.

**Usage:**
```
/runplan <plan filename>
```

## Creating New Commands

To create a new slash command:

1. Create a new `.md` file in `.claude/commands/`
2. Add frontmatter with description:
   ```markdown
   ---
   description: Brief description of what the command does
   ---
   ```
3. Write the command prompt with clear steps
4. Use `$ARGUMENTS` to accept user input (optional)
5. Command will be available as `/filename` (without .md extension)

## Examples

```bash
# Run performance analysis
/ceviz

# Create a new feature plan
/newplan Add fighter comparison tool

# Execute an existing plan
/runplan Feature_Name_2025-11-10.md
```
