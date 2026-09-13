import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import 'app.dart';

// 기기에서 사용 가능한 카메라 목록. CameraScreen 진입 시 재사용한다.
late List<CameraDescription> availableCamerasList;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    availableCamerasList = await availableCameras();
  } on CameraException catch (e) {
    debugPrint('카메라 목록 조회 실패: ${e.code} ${e.description}');
    availableCamerasList = <CameraDescription>[];
  }

  runApp(const EcoDisposalApp());
}
