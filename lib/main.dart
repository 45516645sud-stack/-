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

  // Firebase 프로젝트 연결(firebase_options.dart)이나 App Check 등록이 아직
  // 안 되어 있어도 카메라·정보 표시 같은 나머지 화면은 뜰 수 있어야 하므로,
  // 이 초기화 실패로 앱 전체가 흰 화면에서 멈추지 않게 막는다. 이후 이 두
  // 서비스에 실제로 의존하는 기능(App Check가 붙는 identifyItem 호출,
  // Firestore 조회)은 각자의 화면에서 이미 별도로 에러를 처리한다.
  try {
    await Firebase.initializeApp();

    // identifyItem 백엔드가 유료 API(Vision, 식약처)를 호출하므로, 정식 앱에서
    // 온 요청인지 App Check로 검증한다. 디버그 빌드는 콘솔에 등록한 디버그
    // 토큰으로 통과시킨다: https://firebase.google.com/docs/app-check/flutter/debug-provider
    await FirebaseAppCheck.instance.activate(
      providerAndroid: kDebugMode ? const AndroidDebugProvider() : const AndroidPlayIntegrityProvider(),
      providerApple: kDebugMode ? const AppleDebugProvider() : const AppleAppAttestProvider(),
    );
  } catch (e) {
    debugPrint('Firebase 초기화 실패 (firebase_options 설정을 확인하세요): $e');
  }

  AuthRepository.initialize(appKey: ApiConstants.kakaoJavaScriptKey);

  try {
    availableCamerasList = await availableCameras();
  } on CameraException catch (e) {
    debugPrint('카메라 목록 조회 실패: ${e.code} ${e.description}');
    availableCamerasList = <CameraDescription>[];
  }

  runApp(const EcoDisposalApp());
}
