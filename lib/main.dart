import 'package:camera/camera.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:kakao_map_plugin/kakao_map_plugin.dart';

import 'app.dart';
import 'core/constants/api_constants.dart';

// 기기에서 사용 가능한 카메라 목록. CameraScreen 진입 시 재사용한다.
late List<CameraDescription> availableCamerasList;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp();
  AuthRepository.initialize(appKey: ApiConstants.kakaoJavaScriptKey);

  try {
    availableCamerasList = await availableCameras();
  } on CameraException catch (e) {
    debugPrint('카메라 목록 조회 실패: ${e.code} ${e.description}');
    availableCamerasList = <CameraDescription>[];
  }

  runApp(const EcoDisposalApp());
}
