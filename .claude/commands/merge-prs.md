Execute the PR consolidation and merge workflow.

When invoked, you will:

1. **Ask the user for PR numbers** to consolidate (e.g., "105, 106, 110, 115, 119")
2. **Ask for target branch** (default: master)
3. **Follow the consolidate-prs.md workflow** step by step:
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
