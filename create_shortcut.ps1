# PowerShell script to create desktop shortcut
$SourceFilePath = "$PSScriptRoot\START_ASSET_MANAGER.bat"
$ShortcutPath = "$env:USERPROFILE\Desktop\START Asset Manager.lnk"
$WScriptObj = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptObj.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $SourceFilePath
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "Double-click to start Asset Management System"
$Shortcut.Save()

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Shortcut name: START Asset Manager" -ForegroundColor Cyan
Write-Host "Location: Desktop" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press F5 on your desktop to refresh if you don't see it" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to close"
