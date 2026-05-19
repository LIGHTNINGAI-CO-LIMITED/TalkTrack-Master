param(
    [string]$Repo = "LIGHTNINGAI-CO-LIMITED/TalkTrack-Master",
    [string]$Branch = "main",
    [string]$SkillRoot = "$env:USERPROFILE\.codex\skills\talktrack-master",
    [switch]$InsecureCurlFallback
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step {
    param([string]$Message)
    Write-Host "[talktrack-master-bootstrap] $Message"
}

function Download-With-Fallback {
    param(
        [string]$Url,
        [string]$OutFile
    )

    $errors = New-Object System.Collections.Generic.List[string]

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -TimeoutSec 60
        return "Invoke-WebRequest"
    } catch {
        $errors.Add("Invoke-WebRequest: $($_.Exception.Message)")
    }

    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        try {
            & $curl.Source -L --fail --silent --show-error $Url -o $OutFile
            if ($LASTEXITCODE -eq 0) { return "curl.exe" }
            $errors.Add("curl.exe: exit=$LASTEXITCODE")
        } catch {
            $errors.Add("curl.exe: $($_.Exception.Message)")
        }

        if ($InsecureCurlFallback) {
            try {
                & $curl.Source -k -L --fail --silent --show-error $Url -o $OutFile
                if ($LASTEXITCODE -eq 0) { return "curl.exe -k" }
                $errors.Add("curl.exe -k: exit=$LASTEXITCODE")
            } catch {
                $errors.Add("curl.exe -k: $($_.Exception.Message)")
            }
        }
    } else {
        $errors.Add("curl.exe: not found")
    }

    throw "Download failed. $($errors -join ' | ')"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$workDir = Join-Path $env:TEMP "talktrack-master-bootstrap-$stamp"
$zipPath = Join-Path $workDir "talktrack-master-main.zip"
$extractDir = Join-Path $workDir "extract"
$zipUrl = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"

Write-Step "repo=$Repo branch=$Branch"
Write-Step "target=$SkillRoot"

New-Item -ItemType Directory -Force -Path $workDir | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

$method = Download-With-Fallback -Url $zipUrl -OutFile $zipPath
Write-Step "downloaded via $method"

Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
$source = Get-ChildItem -Path $extractDir -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "SKILL.md") } |
    Select-Object -First 1

if (-not $source) {
    throw "Downloaded archive does not contain SKILL.md at repository root"
}

$skillSource = $source.FullName
$targetParent = Split-Path -Parent $SkillRoot
New-Item -ItemType Directory -Force -Path $targetParent | Out-Null

if (Test-Path -LiteralPath $SkillRoot) {
    $backupPath = "$SkillRoot.backup-$stamp"
    Copy-Item -LiteralPath $SkillRoot -Destination $backupPath -Recurse -Force
    Write-Step "backup=$backupPath"
}

New-Item -ItemType Directory -Force -Path $SkillRoot | Out-Null

$items = @("SKILL.md", "agents", "references", "scripts")
foreach ($item in $items) {
    $sourcePath = Join-Path $skillSource $item
    if (Test-Path -LiteralPath $sourcePath) {
        Copy-Item -LiteralPath $sourcePath -Destination $SkillRoot -Recurse -Force
    }
}
Write-Step "installed latest skill files"

$checkScript = Join-Path $SkillRoot "scripts\check_skill_update.py"
if (Test-Path -LiteralPath $checkScript) {
    python $checkScript --check
} else {
    Write-Step "warning: check script missing after install"
}
