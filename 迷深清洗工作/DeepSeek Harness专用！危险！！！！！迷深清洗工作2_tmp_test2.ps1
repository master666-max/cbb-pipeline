$f = '异世界迷宫最深部_知识库分析酒馆导入v3世界书角色专属世界书角色专属世界书_斯诺.json'
$raw = Get-Content -Raw -Encoding UTF8 $f
$j = $raw | ConvertFrom-Json
$maxUid = ($j.entries | Measure-Object -Property uid -Maximum).Maximum
Write-Output ("maxUid=" + $maxUid)
$e3 = $j.entries | Where-Object { $_.uid -eq 3 }
$old3 = $e3.content
$idx = $old3.IndexOf('【龙化（后期）】')
Write-Output ("dragon idx=" + $idx)
if ($idx -ge 0) {
  $dragonPart = $old3.Substring($idx).Trim()
  $earlyPart = $old3.Substring(0, $idx).Trim()
  Write-Output ("dragonPart len=" + $dragonPart.Length + " earlyPart len=" + $earlyPart.Length)
  $remKeys = @('龙化','龙之风','龙之咆哮')
  $newKeys = @($e3.key | Where-Object { $remKeys -notcontains $_ })
  Write-Output ("new keys: " + ($newKeys -join '|'))
}
