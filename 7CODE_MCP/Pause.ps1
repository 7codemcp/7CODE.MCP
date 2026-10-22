$ErrorActionPreference = 'Stop'
$previousState = $env:SEVEN_CODE_MCP_STATE
try {
    $env:SEVEN_CODE_MCP_STATE = Join-Path $PSScriptRoot '.local'
    & (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -m seven_code_mcp.control pause
    if ($LASTEXITCODE -ne 0) { throw 'Pause failed. Run Stop.ps1.' }
} finally { $env:SEVEN_CODE_MCP_STATE = $previousState }
