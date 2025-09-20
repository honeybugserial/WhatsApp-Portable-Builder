# WhatsApp Portable (Electron Wrapper)

Minimal portable Electron wrapper for **WhatsApp Web** on Windows. Stores data in `./Data`; no MSIX/AppX.

## Quick Start
1. Install **Python 3.9+** into windows.
2. Run: `python buildWhatsApp-Portable.py`
3. Launch: `WhatsApp-Electron\dist\WhatsAppPortable-win32-x64\WhatsAppPortable.exe`

## Features
- Portable profile (`./Data`)
- Modern Chrome UA
- Optional mic/camera prompt
- Auto-installs Node LTS if missing because needed

## Reset
Delete the `Data/` folder to sign out.
