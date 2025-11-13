Execute the PR consolidation and merge workflow with intelligent PR discovery.

When invoked, you will:

1. **Ask how to select PRs** with these options:
   - **Manual**: User provides PR numbers (e.g., "105, 106, 110")
   - **Semantic**: Search by topic/keywords, time range, files, or labels

   Examples of semantic queries:
   - "All PRs about 'fight web refactor' from last 24 hours"
   - "PRs touching backend/api/fighters.py from last week"
   - "PRs with 'enhancement' label created since Nov 10"
   - "My PRs from today"

2. **Execute PR discovery**:
   - For manual: Fetch specified PRs directly
   - For semantic: Use `gh pr list` with filters and `jq` to match criteria
   - Present discovered PRs with summary
   - Ask user to confirm or refine selection

3. **Ask for target branch** (default: master)

4. **Follow the consolidate-prs.md workflow** step by step:
   - Analyze PRs and create consolidation plan
   - Get user approval via ExitPlanMode
   - Execute consolidation with proper conflict resolution
   - Review and address feedback from original PRs
   - Run quality checks (format, lint, sync)
   - Create consolidated PR with comprehensive description
   - Get user approval for merge
   - Merge to target branch and cleanup

**Use TodoWrite** to track progress through all major steps.

**Be systematic**: Don't skip steps, always show the user what you're doing, and ask for confirmation before destructive operations (merge, close PRs).

**Critical**: Always use the BEST implementation when PRs have duplicate code - prefer the most recent, most comprehensive, or most robust version based on your analysis.
