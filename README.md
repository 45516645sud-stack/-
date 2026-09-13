# 수거함 안내

폐의약품·폐건전지를 카메라로 촬영하면 종류와 올바른 폐기 방법을 알려주고,
가장 가까운 수거함까지 카카오내비·T맵·네이버지도로 길안내를 시작하는 앱.

- **플랫폼**: Android, iOS, Web (Flutter 단일 코드베이스)
- **백엔드**: Firebase (Firestore, Cloud Functions, App Check)
- **핵심 기능**: 카메라 촬영/인식 → 식약처 낱알식별 정보 → 내 주변 수거함 지도 → 내비게이션 딥링크

## 시작하기

```bash
flutter pub get
flutter run                 # 연결된 기기/에뮬레이터
flutter run -d chrome        # 웹
```

## 실행 전 채워야 할 값

- `lib/core/constants/api_constants.dart` — Cloud Functions URL, 카카오 JS/네이티브 키
- `firebase_options.dart` — `flutterfire configure`로 생성 (아직 없음)
- `functions/` — `MFDS_API_KEY` secret 등록 (`firebase functions:secrets:set`)
- Firestore `collection_boxes` 컬렉션 — `functions/npm run seed`로 시드 데이터 업로드

## 백엔드 (Cloud Functions)

```bash
cd functions
npm install
npm run build
```
