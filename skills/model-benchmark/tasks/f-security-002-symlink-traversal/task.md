# Task: Safe Workspace Path Resolution (F-security-002)

## Problem Description
Pure lexical path prefix checking (`startsWith(baseDir)`) can be deceived by symlinks pointing outside the workspace or unnormalized traversal sequences.

## Expected Solution
1. Validate resolved paths against workspace bounds.
2. Respect `allowOutsideWorkspace` and `allowDiscoveredSkillFolders` options.
3. Throw appropriate error or rejection when an unsafe boundary escape is attempted.
