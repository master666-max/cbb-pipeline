Write-Output "hello from ps1"
$x = [ordered]@{ a=1; b=$false }
Write-Output ("x.a=" + $x.a)
