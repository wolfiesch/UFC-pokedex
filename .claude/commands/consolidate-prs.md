# Consolidate and Merge Pull Requests

You are helping consolidate multiple related pull requests into a single comprehensive PR, address review feedback, and merge to master.

## Workflow Steps

### 1. Initial Analysis

**Step 1.1: Determine PR Selection Method**

Ask the user how they want to select PRs:

**Option A: Manual PR Numbers**
- User provides explicit PR numbers (e.g., "105, 106, 110")
- Straightforward, works for any PRs

**Option B: Semantic Filtering**
- User provides semantic criteria:
  - **Topic/keywords**: "fight web refactor", "SQLite removal", "image validation"
  - **Time range**: "last 24 hours", "last week", "since Nov 10"
  - **Author**: PRs by specific user
  - **Labels**: PRs with specific labels
  - **File patterns**: PRs touching specific files (e.g., "backend/api/*")

**Step 1.2: Execute PR Discovery**

**For Manual Selection:**
```bash
# User provides: 105, 106, 110
for pr in <numbers>; do
  gh pr view $pr --json number,title,state,createdAt,author,labels,files
done
```

**For Semantic Filtering:**

A. **Search by title/body keywords:**
```bash
# Search for PRs with "fight web" or "fight graph" in title/body
gh pr list --search "fight web in:title,body" --state all --limit 100 \
  --json number,title,body,createdAt,author,labels,files
```

B. **Filter by time range:**
```bash
# Get PRs from last 24 hours
gh pr list --state all --limit 100 \
  --json number,title,createdAt,author,labels,files | \
  jq --arg since "$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)" \
     '.[] | select(.createdAt > $since)'
```

C. **Filter by file patterns:**
```bash
# Get PRs touching fight graph files
gh pr list --state all --limit 100 \
  --json number,title,files | \
  jq '.[] | select(.files[].path | test("fight.?graph|fight.?web"))'
```

D. **Combine filters:**
```bash
# Fight web PRs from last 24 hours
gh pr list --search "fight web in:title,body" --state all --limit 100 \
  --json number,title,body,createdAt,files | \
  jq --arg since "$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)" \
     '.[] | select(.createdAt > $since)'
```

**Step 1.3: Present Discovered PRs**

Show the user:
- PR number, title, author, created date
- Number of files changed
- Labels (if any)
- Brief summary of changes

Ask for confirmation:
- "Found 5 PRs matching 'fight web refactor' from last 24 hours"
- List them with key details
- "Should I consolidate all of these? (or specify which ones)"

**Step 1.4: Fetch Full Metadata**

Once PRs are confirmed:
```bash
for pr in <selected-numbers>; do
  gh pr view $pr --json title,body,headRefName,baseRefName,state,files,reviews,comments
done
```

- Ask which branch to merge into (default: master)
- Analyze file overlap and identify potential conflicts
- Identify which PR has the best implementation for overlapping files

### 2. Create Consolidation Plan
Present a plan to the user showing:
- Layer-by-layer consolidation strategy (which PRs to merge in what order)
- Conflict resolution strategy for duplicate edits
- Which implementation to prefer when multiple PRs touch the same files
- Expected outcome

Use the **ExitPlanMode** tool to present the plan and get user approval before proceeding.

### 3. Execute Consolidation
Once approved:

**Step 3.1: Create consolidated branch**
```bash
git checkout <base-branch>
git pull origin <base-branch>
git checkout -b <consolidated-branch-name>
```

**Step 3.2: Cherry-pick commits layer by layer**
For each PR in the planned order:
```bash
gh pr view <PR-number> --json headRefName --jq '.headRefName'
git fetch origin <branch-name>
git log master..origin/<branch-name> --oneline
git cherry-pick <commit-sha>
```

Resolve conflicts by:
- Reading conflicting files
- Choosing the best implementation based on the plan
- Using `git checkout --theirs` or `git checkout --ours` as appropriate
- Manually editing if needed
- `git add` and `git cherry-pick --continue`

**Step 3.3: Quality checks**
```bash
uv sync                    # Verify dependencies
make format               # Auto-fix formatting
git add -A && git commit -m "Apply code formatting" (if changes)
make lint | head -100     # Check for issues
```

**Step 3.4: Push and create PR**
```bash
git push -u origin <consolidated-branch-name>
gh pr create --title "<Title>" --body "<Comprehensive body>"
```

PR body should include:
- Summary of what's being consolidated
- List of changes from each original PR
- Breaking changes (if any)
- Testing performed
- List of original PRs being superseded
- Co-authored-by credits

### 4. Review Original PR Comments

**Step 4.1: Fetch all review comments**
```bash
gh pr view <PR-number> --json reviews,comments
gh api repos/{owner}/{repo}/pulls/<PR-number>/comments
```

**Step 4.2: Analyze feedback**
For each PR's reviews:
- Extract technical feedback from human reviewers (prioritize over bots)
- Identify actionable issues (ignore generic summaries)
- Categorize as: Critical, Important, Nice-to-have, Nitpick
- Ignore bot-generated summaries without specific line-level feedback

**Step 4.3: Apply valid feedback**
- Address Critical and Important issues immediately
- Consider Nice-to-have if time permits
- Skip Nitpicks unless trivial to fix
- Document decisions in commit messages

**Step 4.4: Commit fixes**
```bash
git add <files>
git commit -m "Address review feedback: <description>"
git push
```

### 5. Final Review and Merge

**Step 5.1: Present summary to user**
Show:
- What was consolidated
- How conflicts were resolved
- Review feedback addressed
- Quality check results
- Link to consolidated PR

**Step 5.2: Ask for merge approval**
Present options:
1. Merge into <base-branch> now
2. Wait for additional review
3. Make changes first

**Step 5.3: Execute merge**
If approved:
```bash
gh pr merge <consolidated-PR> --squash --delete-branch \
  --subject "<Title>" \
  --body "Consolidates PRs #<list>..."
```

**Step 5.4: Cleanup**
```bash
# Close original PRs
for pr in <original-PR-numbers>; do
  gh pr close $pr --comment "Superseded by #<consolidated-PR>"
done

# Update local master
git checkout <base-branch>
git pull origin <base-branch>
```

**Step 5.5: Verification**
- Show final commit SHA
- Verify key changes are present
- Confirm original PRs are closed

## Todo List Management

Use TodoWrite throughout to track:
- [ ] Analyze PRs and create plan
- [ ] Create consolidated branch
- [ ] Layer 1: Cherry-pick PR #X
- [ ] Layer 2: Cherry-pick PR #Y
- [ ] Layer N: Cherry-pick PR #Z
- [ ] Run quality checks
- [ ] Create consolidated PR
- [ ] Review feedback from PR #X
- [ ] Review feedback from PR #Y
- [ ] Apply valid changes
- [ ] Final review and user approval
- [ ] Merge to <base-branch>
- [ ] Close original PRs

Update todo status as you progress through each step.

## Best Practices

### Conflict Resolution
- **Prefer the most recent/comprehensive implementation** when PRs overlap
- **Read both versions** before choosing
- **Manually merge** if both have valuable changes
- **Document rationale** in commit message

### Review Feedback
- **Prioritize human reviews** over AI bot comments
- **Look for specific line-level feedback** not generic summaries
- **Be critical**: Not all review comments are valid
- **Document skipped feedback** with reasoning

### Quality Standards
- Always run `make format` before final merge
- Ensure `uv sync` succeeds
- Check `make lint` output for critical issues
- Prefer squash merges for clean history

### Communication
- Keep user informed at each major step
- Present clear options when decisions needed
- Provide links to PRs and commits
- Show before/after state when making changes

## Error Handling

### Cherry-pick conflicts
If `git cherry-pick` fails:
1. Show conflict files to user
2. Read conflicting sections
3. Apply conflict resolution strategy from plan
4. Continue or ask for guidance if unclear

### Failed quality checks
If lint/tests fail:
1. Show first 50-100 lines of errors
2. Determine if issues are pre-existing or introduced
3. Fix if introduced by consolidation
4. Document if pre-existing

### Merge failures
If merge fails:
1. Check for branch protection rules
2. Verify CI status
3. Ask user for next steps
4. Document any blockers

## Example Semantic Queries

### By Topic/Keywords
```
User: "Find all PRs about fight web refactor from the last 24 hours"

Execute:
gh pr list --search "fight web OR fight graph in:title,body" --state all --limit 100 \
  --json number,title,body,createdAt,author,files | \
  jq --arg since "$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)" \
     '[.[] | select(.createdAt > $since)]'
```

### By File Patterns
```
User: "Find PRs touching fight graph components from last week"

Execute:
gh pr list --state all --limit 100 \
  --json number,title,createdAt,files | \
  jq --arg since "$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)" \
     '[.[] | select(.createdAt > $since and (.files[].path | test("FightGraph|FightWeb|fight-graph")))]'
```

### By Author and Time
```
User: "My PRs from today"

Execute:
gh pr list --author @me --state all --limit 100 \
  --json number,title,createdAt | \
  jq --arg since "$(date -u +%Y-%m-%dT00:00:00Z)" \
     '[.[] | select(.createdAt > $since)]'
```

### By Labels
```
User: "All enhancement PRs from this week"

Execute:
gh pr list --label enhancement --state all --limit 100 \
  --json number,title,createdAt,labels | \
  jq --arg since "$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)" \
     '[.[] | select(.createdAt > $since)]'
```

### Complex Queries
```
User: "SQLite removal PRs touching backend from last 2 days"

Execute:
gh pr list --search "sqlite OR SQLite in:title,body" --state all --limit 100 \
  --json number,title,body,createdAt,files | \
  jq --arg since "$(date -u -v-2d +%Y-%m-%dT%H:%M:%SZ)" \
     '[.[] | select(.createdAt > $since and (.files[].path | test("^backend/")))]'
```

## Date Handling Notes

**macOS (BSD date):**
```bash
date -u -v-24H +%Y-%m-%dT%H:%M:%SZ  # 24 hours ago
date -u -v-7d +%Y-%m-%dT%H:%M:%SZ   # 7 days ago
date -u +%Y-%m-%dT00:00:00Z         # Today at midnight
```

**Linux (GNU date):**
```bash
date -u -d "24 hours ago" +%Y-%m-%dT%H:%M:%SZ
date -u -d "7 days ago" +%Y-%m-%dT%H:%M:%SZ
date -u -d "today 00:00:00" +%Y-%m-%dT%H:%M:%SZ
```

Use appropriate syntax based on detected OS.

## Notes

- This workflow assumes GitHub CLI (`gh`) is installed and authenticated
- Adjust git commands based on repository's branch protection settings
- Always verify base branch before creating consolidated branch
- Consider running tests locally before pushing if test suite is fast
- Semantic filtering requires `jq` for JSON processing
- Date calculations differ between macOS and Linux - detect OS first
