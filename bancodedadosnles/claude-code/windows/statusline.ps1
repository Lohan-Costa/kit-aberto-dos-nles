$json = [Console]::In.ReadToEnd() | ConvertFrom-Json

$ESC = [char]27
$GREEN = "$ESC[32m"
$YELLOW = "$ESC[33m"
$RED = "$ESC[31m"
$CYAN = "$ESC[36m"
$RESET = "$ESC[0m"

function Get-Bar($pct) {
    $width = 10
    $filled = [math]::Floor($pct * $width / 100)
    if ($filled -lt 0) { $filled = 0 }
    if ($filled -gt $width) { $filled = $width }
    $empty = $width - $filled
    return ('#' * $filled) + ('.' * $empty)
}

function Get-Color($pct) {
    if ($pct -ge 90) { return $RED }
    elseif ($pct -ge 70) { return $YELLOW }
    else { return $GREEN }
}

$model = $json.model.display_name

$ctxPctRaw = $json.context_window.used_percentage
if ($null -eq $ctxPctRaw) { $ctxPct = 0 } else { $ctxPct = [math]::Floor([double]$ctxPctRaw) }
# Grava o percentual por sessão para o gancho de aviso de contexto (aviso_contexto.py, PostToolUse): a partir de
# 85 % ele pede checkpoint (handoff, banco, commit) e nenhuma tarefa nova — pedido do autor, 2026-10-11.
try {
    $sid = $json.session_id
    if ($sid) {
        $dir = Join-Path $env:USERPROFILE ".claude\state"
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
        Set-Content -Path (Join-Path $dir "ctx_$sid.txt") -Value $ctxPct -Encoding ascii
    }
} catch { }
$ctxBar = Get-Bar $ctxPct
$ctxColor = Get-Color $ctxPct

$line = "$CYAN$model$RESET  ctx $ctxColor$ctxBar$RESET $ctxPct%"

$fiveHour = $json.rate_limits.five_hour.used_percentage
if ($null -ne $fiveHour) {
    $fhPct = [math]::Floor([double]$fiveHour)
    $fhBar = Get-Bar $fhPct
    $fhColor = Get-Color $fhPct
    $line += "   5h $fhColor$fhBar$RESET $fhPct%"

    $resetsAt = $json.rate_limits.five_hour.resets_at
    if ($null -ne $resetsAt) {
        $resetDate = [DateTimeOffset]::FromUnixTimeSeconds([int64]$resetsAt).LocalDateTime
        $remaining = $resetDate - (Get-Date)
        if ($remaining.TotalSeconds -gt 0) {
            $h = [math]::Floor($remaining.TotalHours)
            $m = $remaining.Minutes
            $line += "  resets in ${h}h${m}m"
        }
    }
}

Write-Output $line
