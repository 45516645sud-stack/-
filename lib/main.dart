import 'dart:async' show unawaited;

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

  AuthRepository.initialize(appKey: ApiConstants.kakaoJavaScriptKey);

  try {
    availableCamerasList = await availableCameras();
  } on CameraException catch (e) {
    debugPrint('카메라 목록 조회 실패: ${e.code} ${e.description}');
    availableCamerasList = <CameraDescription>[];
  }

  runApp(const EcoDisposalApp());

  // Firebase/App Check는 첫 화면(카메라 촬영)에는 필요 없고, 나중에
  // item_info·collection_map 화면에서 실제로 쓰일 때 필요하다. 여기서
  // await하면 firebase_options.dart 미설정이나 네트워크 문제로 실패했을 때
  // (특히 웹에서 CDN 로드 실패는 일반 try/catch로 못 잡히는 경우가 있다)
  // 앱 전체가 첫 프레임도 못 그리고 멈춘다. runApp() 이후 백그라운드로
  // 돌려서 부팅을 막지 않게 한다.
  unawaited(_initializeFirebase());
}

Future<void> _initializeFirebase() async {
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
}
