$path = 'logs\chat_page_dom.log'
$out = 'artifacts/integration-logs/tail_capture.txt'
if (Test-Path $out) { Remove-Item $out -Force }
$pattern = 'RETRY_EMOTE_REPLACE|RENDER_PROBE'
$end = (Get-Date).AddSeconds(600)
$fs = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
$sr = New-Object System.IO.StreamReader($fs)
$sr.BaseStream.Seek(0, [System.IO.SeekOrigin]::End) > $null
while((Get-Date) -lt $end) {
  $line = $sr.ReadLine()
  if ($line -ne $null) {
    if ($line -match $pattern) {
      $line | Out-File $out -Append
      Write-Output $line
    }
  } else {
    Start-Sleep -Milliseconds 200
  }
}
$sr.Close()
$fs.Close()
if (Test-Path $out) { Get-Content $out -Tail 2000 } else { Write-Output 'NO_OUTPUT_FILE' }
