param(
    [ValidateSet("talktrack-agent", "talktrack-master", "both")]
    [string]$Skill = "both",

    [ValidateSet("ReadOnly", "Write")]
    [string]$Mode = "Write",

    [switch]$InstallFromLocalRepo,

    [string]$AgentMinVersion = "v0.1.14",
    [string]$MasterMinVersion = "v0.4.2",
    [string]$ProjectRoot = "D:\闪电智能",
    [string]$SkillRootBase = "$env:USERPROFILE\.codex\skills"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step {
    param([string]$Message)
    Write-Host "[talktrack-preflight] $Message"
}

function Get-SkillSpec {
    param([string]$Name)
    if ($Name -eq "talktrack-agent") {
        return [pscustomobject]@{
            Name = "talktrack-agent"
            MinVersion = $AgentMinVersion
            InstallSource = Join-Path $ProjectRoot "github\TalkTrack-Agent\codex-skills\talktrack-agent"
            InstallTarget = Join-Path $SkillRootBase "talktrack-agent"
        }
    }
    if ($Name -eq "talktrack-master") {
        return [pscustomobject]@{
            Name = "talktrack-master"
            MinVersion = $MasterMinVersion
            InstallSource = Join-Path $ProjectRoot "github\TalkTrack-Master"
            InstallTarget = Join-Path $SkillRootBase "talktrack-master"
        }
    }
    throw "Unsupported skill: $Name"
}

function Get-SkillVersion {
    param([string]$SkillPath)
    $skillFile = Join-Path $SkillPath "SKILL.md"
    if (-not (Test-Path -LiteralPath $skillFile)) {
        throw "SKILL.md missing: $skillFile"
    }
    $line = Get-Content -LiteralPath $skillFile -Encoding UTF8 |
        Where-Object { $_ -match '^\s*version\s*:' } |
        Select-Object -First 1
    if (-not $line) {
        throw "version field missing in $skillFile"
    }
    return (($line -replace '^\s*version\s*:\s*', '') -replace '["'']', '').Trim()
}

function Convert-VersionTuple {
    param([string]$Version)
    $matches = [regex]::Matches($Version, '\d+')
    $values = @()
    foreach ($match in $matches) {
        $values += [int]$match.Value
    }
    return $values
}

function Compare-SemverLike {
    param(
        [string]$Left,
        [string]$Right
    )
    $leftValues = Convert-VersionTuple $Left
    $rightValues = Convert-VersionTuple $Right
    $count = [Math]::Max($leftValues.Count, $rightValues.Count)
    for ($i = 0; $i -lt $count; $i++) {
        $l = if ($i -lt $leftValues.Count) { $leftValues[$i] } else { 0 }
        $r = if ($i -lt $rightValues.Count) { $rightValues[$i] } else { 0 }
        if ($l -gt $r) { return 1 }
        if ($l -lt $r) { return -1 }
    }
    return 0
}

function Install-SkillFromLocalRepo {
    param($Spec)
    if (-not (Test-Path -LiteralPath (Join-Path $Spec.InstallSource "SKILL.md"))) {
        throw "local source missing for $($Spec.Name): $($Spec.InstallSource)"
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    if (Test-Path -LiteralPath $Spec.InstallTarget) {
        $backupPath = "$($Spec.InstallTarget).backup-$stamp"
        Copy-Item -LiteralPath $Spec.InstallTarget -Destination $backupPath -Recurse -Force
        Write-Step "$($Spec.Name) backup=$backupPath"
    }

    New-Item -ItemType Directory -Force -Path $Spec.InstallTarget | Out-Null
    foreach ($item in @("SKILL.md", "agents", "references", "scripts")) {
        $sourcePath = Join-Path $Spec.InstallSource $item
        if (Test-Path -LiteralPath $sourcePath) {
            Copy-Item -LiteralPath $sourcePath -Destination $Spec.InstallTarget -Recurse -Force
        }
    }
    Write-Step "$($Spec.Name) installed_from_local_repo"
}

function Invoke-UpdateCheck {
    param($Spec)
    $checkScript = Join-Path $Spec.InstallTarget "scripts\check_skill_update.py"
    if (-not (Test-Path -LiteralPath $checkScript)) {
        throw "update check script missing: $checkScript"
    }

    $output = & python $checkScript --check --json 2>&1
    $text = ($output | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "update check failed for $($Spec.Name): $text"
    }

    try {
        return $text | ConvertFrom-Json
    } catch {
        throw "update check returned invalid JSON for $($Spec.Name): $text"
    }
}

function Test-Skill {
    param($Spec)

    if ($InstallFromLocalRepo) {
        Install-SkillFromLocalRepo $Spec
    }

    $localVersion = Get-SkillVersion $Spec.InstallTarget
    $cmp = Compare-SemverLike $localVersion $Spec.MinVersion
    Write-Step "$($Spec.Name) local_version=$localVersion min_required=$($Spec.MinVersion)"
    if ($cmp -lt 0) {
        throw "$($Spec.Name) is stale. local=$localVersion min_required=$($Spec.MinVersion). Run with -InstallFromLocalRepo or update the skill before backend writes."
    }

    if ($Mode -eq "Write") {
        $status = Invoke-UpdateCheck $Spec
        Write-Step "$($Spec.Name) remote_version=$($status.remote_version) status=$($status.status)"
        if ($status.status -ne "up_to_date" -and $status.status -ne "local_newer") {
            throw "$($Spec.Name) is not write-ready. update_status=$($status.status). Backend writes are blocked."
        }
    } else {
        Write-Step "$($Spec.Name) read_only_mode_update_check_skipped"
    }
}

$skills = if ($Skill -eq "both") {
    @("talktrack-agent", "talktrack-master")
} else {
    @($Skill)
}

try {
    foreach ($skillName in $skills) {
        Test-Skill (Get-SkillSpec $skillName)
    }
    Write-Host "PREFLIGHT_PASS skill=$Skill mode=$Mode"
    exit 0
} catch {
    Write-Host "PREFLIGHT_FAIL skill=$Skill mode=$Mode"
    Write-Host $_.Exception.Message
    Write-Host "For write tasks, stop here. Do not ask for backend authorization until this preflight passes."
    exit 2
}
