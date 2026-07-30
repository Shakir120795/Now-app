# Luxe Commerce — Mobile (Flutter)

Material 3 · Riverpod · GoRouter · Dio · Hive. Clean Architecture, feature-based.

## Prerequisites
- Flutter stable (>= 3.24), Dart >= 3.5

## Run
```bash
flutter pub get
dart run build_runner build --delete-conflicting-outputs   # codegen (once models land)
flutter run
```

## Structure
See [`../docs/FOLDER_STRUCTURE_MOBILE.md`](../docs/FOLDER_STRUCTURE_MOBILE.md).

## Status — Phase 3 core complete
Design matches the reference NOW app (dark home + light cart, red CTA, gold prices).
Implemented screens: Onboarding, Login/OTP (+ guest), Home, Product Detail, Cart/Checkout,
Orders, Order Tracking, Profile, Drawer — wired to the FastAPI backend via Dio + Riverpod +
GoRouter. See `design/preview.html` and `design/preview2.html` for rendered mockups.

### Point the app at your backend
The API base URL is a compile-time define (`lib/core/config/app_config.dart`):
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1   # Android emulator → host
```
`10.0.2.2` is the host machine from the Android emulator; use your LAN IP for a real device.

### Fonts
The theme references `Poppins`; add it to `pubspec.yaml` fonts or remove `fontFamily`
in `app_theme.dart` to fall back to the system sans.
