param(
    [string]$EntryPoint = "app/main.py",
    [string]$Name = "Jarvis43Day",
    [switch]$Clean
)

Write-Host "Building Windows executable with PyInstaller..."
if ($Clean) {
    if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
    if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
    if (Test-Path "$Name.spec") { Remove-Item "$Name.spec" -Force }
}

Write-Host ""
Write-Host "Note:"
Write-Host "- OCR needs Tesseract installed on the target machine (not bundled by default)."
Write-Host "- WhatsApp automation relies on WhatsApp Web login in your browser."
Write-Host ""

pyinstaller `
  --noconfirm `
  --windowed `
  --name $Name `
  --hidden-import "PySide6.QtXml" `
  --hidden-import "pyttsx3.drivers.sapi5" `
  --collect-submodules "pytesseract" `
  --collect-submodules "cv2" `
  $EntryPoint

Write-Host "Build completed. Check dist/$Name/"
