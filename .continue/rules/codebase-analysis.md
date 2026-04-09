---
globs: ["**/*"]
description: Policy for efficient codebase exploration and analysis in Continue.dev
alwaysApply: true
---

When you need to understand, analyze, or find patterns across multiple files (e.g., test coverage, data flow, authentication logic, refactoring opportunities):

1. First use the **codebase** tool for semantic/relevant snippet retrieval — it is the most efficient for high-level understanding.
2. Supplement with:
   - grep_search for exact patterns or keywords
   - file_glob_search for file discovery
   - ls / view_subdirectory for structure
3. Only fall back to reading individual files with read_file after narrowing down with the above.
4. For broad tasks like "analyze test coverage", start with codebase + grep_search.
