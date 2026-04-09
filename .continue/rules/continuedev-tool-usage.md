---
globs: '["**/*"]'
description: This rule should be applied when working in Continue.dev
  environment to ensure I use the correct tools for file operations and other
  tasks.
---

In Continue.dev environment, use only these tools:
- File operations: read_file, create_new_file, edit_existing_file, read_file_range
- Search: file_glob_search, grep_search, codebase
- Navigation: ls, view_subdirectory, view_repo_map
- Commands: run_terminal_command
- Other: fetch_url_content, read_skill, view_diff, read_currently_open_file, create_rule_block

Prefer using these tools first when possible. For file creation, prefer create_new_file. For file editing, prefer edit_existing_file or single_find_and_replace.
