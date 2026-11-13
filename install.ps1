# Install the published Apple UI Skill package. Requires Python 3.10+.
# Example: & ([scriptblock]::Create((irm https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/install.ps1))) -Agent claude
[CmdletBinding()]
param(
    [ValidateSet('codex', 'claude', 'gemini')][string]$Agent = 'codex',
    [ValidateSet('user', 'project')][string]$Scope = 'user',
    [string]$Destination,
    [string]$ManifestUrl = 'https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/distribution.json',
    [switch]$Update,
    [switch]$Recover
)
$ErrorActionPreference = 'Stop'
if ($Update -and $Recover) { throw 'Choose either -Update or -Recover.' }

$pythonCommand = $null
$pythonPrefix = @()
foreach ($candidate in @('py', 'python3', 'python')) {
    $resolved = Get-Command $candidate -ErrorAction SilentlyContinue | Select-Object -First 1
    if (!$resolved) { continue }
    # Keep even a single launcher flag as an array: PowerShell unwraps the
    # output of an if expression and scalar splatting can invoke Python stdin.
    [string[]]$prefix = @()
    if ($candidate -eq 'py') { $prefix = @('-3') }
    try {
        & $resolved.Source @prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonCommand = $resolved.Source
            $pythonPrefix = @($prefix)
            break
        }
    } catch { }
}
if (!$pythonCommand) { throw 'Install Python 3.10 or newer, then run this installer again.' }

$installerTemp = Join-Path ([System.IO.Path]::GetTempPath()) ('apple-ui-install-' + [guid]::NewGuid().ToString('N') + '.py')
try {
    Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/installer.py' -OutFile $installerTemp
    $arguments = @($installerTemp, '--agent', $Agent, '--scope', $Scope, '--manifest-url', $ManifestUrl)
    if ($Destination) { $arguments += @('--destination', $Destination) }
    if ($Update) { $arguments += '--update' }
    if ($Recover) { $arguments += '--recover' }
    & $pythonCommand @pythonPrefix @arguments
    if ($LASTEXITCODE -ne 0) { throw "Apple UI Skill installation exited with code $LASTEXITCODE." }
} finally {
    if (Test-Path -LiteralPath $installerTemp) { Remove-Item -LiteralPath $installerTemp }
}
