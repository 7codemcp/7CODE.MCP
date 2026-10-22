param([ValidateSet('Status','Enable','Disable')][string]$Action='Status')
$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot
$state = Join-Path $project '.local'
$venv = Join-Path $project '.venv\Scripts\python.exe'
$py = if (Test-Path -LiteralPath $venv) { $venv } else { 'python' }
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $project 'src'
    & $py -m seven_code_mcp.memory_cli $Action --state $state
    if ($LASTEXITCODE -ne 0) { throw '7CODE memory control failed.' }
} finally {
    $env:PYTHONPATH = $oldPythonPath
}
