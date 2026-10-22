# 7CODE MCP

Windows-based MCP project with local desktop/file automation and opt-in SQLite project memory.

## Run

Launch 7CODE.cmd on Windows to access the terminal control menu.
Application source and tests are under windows-local-mcp-main/.
The original local ZIP includes two prepacked Windows Tunnel runtime archives. To keep the source repository lightweight, binary runtime archives are not committed here. Run Setup.ps1 to download the official Tunnel client when setting up the service.

## Security

Memory must be enabled locally through the control menu. Do not commit credentials,
local state, SQLite memory files, audit logs, backups or API keys. Commands run with
the current Windows user's permissions and are not an OS security sandbox.

## Licensing

See windows-local-mcp-main/LICENSE and
windows-local-mcp-main/7CODE-ATTRIBUTION.md for the upstream MIT terms and
7CODE project modifications.