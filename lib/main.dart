import 'package:camera/camera.dart';
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:kakao_map_plugin/kakao_map_plugin.dart';

import 'app.dart';
import 'core/constants/api_constants.dart';

// 기기에서 사용 가능한 카메라 목록. CameraScreen 진입 시 재사용한다.
late List<CameraDescription> availableCamerasList;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp();

  // identifyItem 백엔드가 유료 API(Vision, 식약처)를 호출하므로, 정식 앱에서
  // 온 요청인지 App Check로 검증한다. 디버그 빌드는 콘솔에 등록한 디버그
  // 토큰으로 통과시킨다: https://firebase.google.com/docs/app-check/flutter/debug-provider
  await FirebaseAppCheck.instance.activate(
    androidProvider: kDebugMode ? AndroidProvider.debug : AndroidProvider.playIntegrity,
    appleProvider: kDebugMode ? AppleProvider.debug : AppleProvider.appAttest,
  );

  AuthRepository.initialize(appKey: ApiConstants.kakaoJavaScriptKey);

  try {
    availableCamerasList = await availableCameras();
  } on CameraException catch (e) {
    debugPrint('카메라 목록 조회 실패: ${e.code} ${e.description}');
    availableCamerasList = <CameraDescription>[];
  }

  runApp(const EcoDisposalApp());
}
