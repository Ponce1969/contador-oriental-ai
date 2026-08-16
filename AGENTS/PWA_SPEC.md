# PWA_SPEC.md — Progressive Web App & Branding Specification

## Overview

Contador Oriental is served as a Progressive Web App (PWA) via Flet Web.
This enables seamless installation across Android (Chrome), iOS (Safari), Windows, macOS, and Linux without compiling separate native platform binaries.

## Architecture

1. **Host**: Served by Flet Web / FastAPI on port `8550` (or `APP_PORT`).
2. **PWA Manifest**: Located at `assets/manifest.json`. Overrides default Flet metadata.
3. **Asset Resolution**: Files placed in `assets/` and `assets/icons/` take precedence over default Flet web assets.
4. **Display Mode**: `standalone` (fullscreen, no browser URL bar or navigation controls).
5. **Theme Colors**:
   - `background_color`: `#f8fafc` (Light background)
   - `theme_color`: `#1e3a8a` (Contador Oriental Primary Navy/Blue)

## File Structure

```
assets/
├── manifest.json                  # PWA configuration manifest
├── favicon.png                    # Browser tab icon (32x32 / 64x64)
├── icon-gastos.ico                # Desktop Windows icon
└── icons/
    ├── icon-192.png               # Standard Android home screen icon (192x192)
    ├── icon-512.png               # High-res splash / app store icon (512x512)
    ├── icon-maskable-512.png      # Android adaptive maskable icon (512x512)
    ├── apple-touch-icon-192.png   # iOS Safari home screen icon (192x192)
    └── loading-animation.png      # Custom startup animation
```

## PWA Manifest (`assets/manifest.json`) Specification

```json
{
  "name": "Contador Oriental",
  "short_name": "Contador",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#1e3a8a",
  "description": "Asistente contable con IA para familias uruguayas",
  "orientation": "portrait-primary",
  "prefer_related_applications": false,
  "icons": [
    {
      "src": "icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "icons/icon-maskable-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
```

## Platform Behaviors

- **Android (Chrome)**: Detects manifest and prompts "Install Contador Oriental" or "Add to Home Screen". Launches with standalone window and splash screen.
- **iOS (Safari)**: User taps "Share" -> "Add to Home Screen". Uses `apple-touch-icon-192.png` and runs in standalone web app sandbox.
- **Desktop (Chrome/Edge/Brave)**: Displays install icon in address bar, creates desktop/start menu shortcut running in dedicated app window.
- **Updates**: Instant. Every `git pull` & container restart updates the app across all installed devices without requiring app store approvals or APK updates.
