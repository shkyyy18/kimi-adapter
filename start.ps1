#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
python -m kimi_adapter.cli @args
