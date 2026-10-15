# Sign in to NotebookLM on this PC and copy the session to the server that runs the pipeline.
# The server has no browser, so the Google sign-in happens here. Put a desktop shortcut to:
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File login-and-push.ps1 -Server user@host
param(
    [Parameter(Mandatory)] [string] $Server,                       # e.g. me@100.64.0.10 (SSH key auth)
    [string] $Notebooklm = "notebooklm",                            # path to the CLI in your venv
    [string] $RemoteCheck = "~/lecture-notes-pipeline/scripts/check-auth.sh"
)
$state = "$env:USERPROFILE\.notebooklm\profiles\default\storage_state.json"

Write-Host "A browser opens: sign in, wait for NotebookLM, then come back here and press Enter." -ForegroundColor Cyan
& $Notebooklm login --browser msedge
if ($LASTEXITCODE -ne 0) { Write-Host "Login failed." -ForegroundColor Red; Read-Host "Enter to close"; exit 1 }

Write-Host "Copying the login to $Server ..." -ForegroundColor Cyan
ssh -o BatchMode=yes $Server "mkdir -p ~/.notebooklm/profiles/default && chmod 700 ~/.notebooklm"
scp -q $state "${Server}:.notebooklm/profiles/default/storage_state.json"
ssh -o BatchMode=yes $Server "chmod 600 ~/.notebooklm/profiles/default/storage_state.json && $RemoteCheck --confirm"
if ($LASTEXITCODE -eq 0) { Write-Host "Done: the server is signed in." -ForegroundColor Green }
else { Write-Host "Copied, but the server still can't sign in: try again." -ForegroundColor Yellow }
Start-Sleep 4
