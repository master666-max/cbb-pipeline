$events = Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000} -MaxEvents 30 -ErrorAction SilentlyContinue
$comfy = $events | Where-Object { $_.Message -match 'Comfy' } | Select-Object -First 3
if (-not $comfy) { Write-Output "NO_COMFY_EVENTS_IN_LAST_30_CRASHES" }
foreach ($e in $comfy) {
  Write-Output ("TIME: " + $e.TimeCreated)
  Write-Output ($e.Message -split "`n" | Select-Object -First 12 | Out-String)
  Write-Output "--------"
}
