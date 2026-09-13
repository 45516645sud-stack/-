import 'dart:async' show unawaited;

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:kakao_map_plugin/kakao_map_plugin.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

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

  // Supabase 초기화(+ 익명 로그인)는 첫 화면(카메라 촬영)에는 필요 없고
  // item_info·collection_map 화면에서 실제로 쓰일 때 필요하다. 네트워크
  // 문제로 실패해도 앱 부팅 자체는 막지 않도록 runApp() 이후 백그라운드로
  // 돌린다.
  unawaited(initializeSupabase());
}

/// 다른 화면에서도(예: 세션이 아직 없을 때) 재사용할 수 있도록 top-level로 둔다.
Future<void> initializeSupabase() async {
  try {
    await Supabase.initialize(
      url: ApiConstants.supabaseUrl,
      publishableKey: ApiConstants.supabasePublishableKey,
    );

    // identify-item Edge Function은 유효한 Supabase 세션(JWT)이 없으면
    // 게이트웨이 단계에서 401로 막힌다. 로그인 화면이 없는 앱이라 익명
    // 인증으로 최소한의 토큰을 확보해 둔다 — Firebase App Check가 하던
    // "정식 클라이언트인지 검증" 역할의 대체제. App Check의 기기 증명만큼
    // 강력하진 않지만 URL만 알아낸 임의 호출은 막아준다.
    if (Supabase.instance.client.auth.currentSession == null) {
      await Supabase.instance.client.auth.signInAnonymously();
    }
  } catch (e) {
    debugPrint('Supabase 초기화 실패: $e');
  }
}
