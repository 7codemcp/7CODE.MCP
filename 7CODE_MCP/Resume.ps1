$ErrorActionPreference = 'Stop'
$previousState = $env:SEVEN_CODE_MCP_STATE
try {
    $env:SEVEN_CODE_MCP_STATE = Join-Path $PSScriptRoot '.local'
    & (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -m seven_code_mcp.control resume
    if ($LASTEXITCODE -ne 0) { throw 'Resume failed.' }
} finally { $env:SEVEN_CODE_MCP_STATE = $previousState }
