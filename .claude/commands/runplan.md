---
description: Implement a feature plan from docs/plans/ directory and update status
---

Implement the plan from: @$1

Please follow these steps:

1. **Review the plan thoroughly**:
   - Understand all requirements and implementation steps
   - Identify dependencies and prerequisites
   - Note any potential challenges mentioned

2. **Create a todo list** using TodoWrite:
   - Break down the plan into actionable tasks
   - Track progress as you implement each step
   - Mark tasks as in_progress → completed as you work

3. **Implement the plan**:
   - Follow the implementation steps from the plan
   - Write clean, well-tested code
   - Follow project conventions from `docs/ai-assistants/CLAUDE.md`
   - Run tests and verify functionality
   - Handle edge cases mentioned in the plan

4. **Update the plan document** at `$1` when complete:
   - Add an implementation status section at the TOP of the file
   - Include the following format:

```markdown
---
**IMPLEMENTATION STATUS**: ✅ COMPLETED | 🚧 IN PROGRESS | ❌ BLOCKED
**Implemented Date**: YYYY-MM-DD
**Implementation Summary**: Brief summary of what was implemented
---

## Usage

[Instructions on how to use the new feature/functionality]

## What Was Implemented

- List of completed items
- Key files modified/created
- Any deviations from the original plan

## Testing

- How to test the feature
- Any test files created

---

[Original plan content preserved below]
```

5. **Provide a summary** including:
   - What was successfully implemented
   - Any challenges encountered
   - How to use the new functionality
   - Next steps or follow-up items (if any)

Remember to be thorough and follow best practices throughout the implementation.
