# 7CODE MCP | Project Continuity Edition (0.4.0)

Brand: 7CODE. Maintained custom additions: opt-in project memory, new local control options and ASCII terminal splash.

## Launch
Open \`..\7CODE.cmd\` or \`Control.cmd\` and complete Setup/Configure as before. Existing tunnel and MCP tools are preserved; no automatic migration or replacement of an already connected server takes place.

## Memory (local SQLite, disabled by default)
In Control menu:
- 11 Enable memory (on this PC only).
- 12 Disable memory (preserves saved records).
- 13 Check memory state.

The database lives at \`.local\memory.sqlite3\` under the service's private Windows ACL. The existing protected-path guard prevents MCP tools from reading or editing the database. Use the same .local directory across conversations to keep project history. Do not delete it during upgrades.

Available MCP tools:
- \`memory_status\`: check toggle and counts.
- \`memory_project_create\`: register an existing project folder and objective.
- \`memory_project_list\`: list projects at start of a new conversation.
- \`memory_project_context\`: retrieve current objective, last checkpoints and event history.
- \`memory_checkpoint\`: save verified outcomes, errors, decisions, blockers and next exact step.
- \`memory_search\`: find earlier checkpoint details.

When on, tool calls are recorded automatically as metadata-only actions linked to project directory paths. Deliberately **not** recorded: full chat transcripts, passwords, keys, screenshots, file contents, or command output. Model must save important information via \`memory_checkpoint\`. No user-facing system can guarantee reconstruction of unseen conversations; cross-chat continuity requires reconnecting this MCP server and calling its memory tools.

Switch is **not remotely controllable** over MCP. To hard-stop work, keep using the existing local pause controls. Existing file editing, desktop, search and command tools are kept intact.

## Licensing and authorship
7CODE branding and new original contributions are designated Copyright (c) 2026 7CODE. The original Windows Local MCP contribution retains its MIT License in LICENSE as required. Branding is not a legal transfer of existing contributors' copyrights.
