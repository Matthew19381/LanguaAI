$action = New-ScheduledTaskAction -Execute 'python' -Argument '-m uvicorn backend.main:app --host 127.0.0.1 --port 8001' -WorkingDirectory 'C:\GoogleDriveSync\Projekty\LinguaAI'
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'LinguaAI-Backend' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'LinguaAI Backend Server' -Force
Write-Host 'Scheduled task created successfully'
