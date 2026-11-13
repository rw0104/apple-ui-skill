# Exercise the native Python-launcher path without network or global install.
$ErrorActionPreference = 'Stop'
$bootstrapRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$probeRoot = Join-Path ([IO.Path]::GetTempPath()) ('apple-ui-bootstrap-proof-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $probeRoot | Out-Null
$priorOutput = $env:AUI_BOOTSTRAP_TEST_OUTPUT
$env:AUI_BOOTSTRAP_TEST_OUTPUT = Join-Path $probeRoot 'received.json'
try {
    if (!(Get-Command py -ErrorAction SilentlyContinue)) { throw 'This regression requires the Windows Python launcher py.exe.' }
    function Invoke-WebRequest {
        param([switch]$UseBasicParsing, [string]$Uri, [string]$OutFile)
        if ($Uri -ne 'https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/installer.py') { throw 'Unexpected bootstrap URL' }
        @'
import json, os, sys
from pathlib import Path
Path(os.environ['AUI_BOOTSTRAP_TEST_OUTPUT']).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')
'@ | Set-Content -LiteralPath $OutFile -Encoding utf8
    }
    $probeDestination = Join-Path $probeRoot 'explicit destination'
    & ([scriptblock]::Create((Get-Content -LiteralPath (Join-Path $bootstrapRoot 'install.ps1') -Raw))) -Agent claude -Scope project -Destination $probeDestination -Update
    if (!(Test-Path -LiteralPath $env:AUI_BOOTSTRAP_TEST_OUTPUT)) { throw 'Python did not execute the downloaded script.' }
    $received = Get-Content -LiteralPath $env:AUI_BOOTSTRAP_TEST_OUTPUT -Raw | ConvertFrom-Json
    $expected = @('--agent', 'claude', '--scope', 'project', '--manifest-url', 'https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/distribution.json', '--destination', $probeDestination, '--update')
    if (($received | ConvertTo-Json -Compress) -ne ($expected | ConvertTo-Json -Compress)) { throw 'Installer arguments did not reach native Python intact.' }

    # The ordinary irm | iex pattern has no explicit parameters. The probe
    # intercepts the download, so this cannot install into a user skill path.
    Remove-Item -LiteralPath $env:AUI_BOOTSTRAP_TEST_OUTPUT
    Get-Content -LiteralPath (Join-Path $bootstrapRoot 'install.ps1') -Raw | Invoke-Expression
    if (!(Test-Path -LiteralPath $env:AUI_BOOTSTRAP_TEST_OUTPUT)) { throw 'Default iex mode did not execute the downloaded script.' }
    $received = Get-Content -LiteralPath $env:AUI_BOOTSTRAP_TEST_OUTPUT -Raw | ConvertFrom-Json
    $expected = @('--agent', 'codex', '--scope', 'user', '--manifest-url', 'https://raw.githubusercontent.com/rw0104/apple-ui-skill/main/distribution.json')
    if (($received | ConvertTo-Json -Compress) -ne ($expected | ConvertTo-Json -Compress)) { throw 'Default one-line arguments did not reach native Python intact.' }
    'Windows native launcher: explicit scriptblock and default iex paths passed.'
} finally {
    $env:AUI_BOOTSTRAP_TEST_OUTPUT = $priorOutput
    $resolved = [IO.Path]::GetFullPath($probeRoot)
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if (!$resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected probe cleanup path.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
