/// Supabase 프로젝트 접속 정보 및 외부 API 관련 상수.
/// 여기 있는 키들은 모두 클라이언트에 노출되어도 되는 공개 키다.
/// (Supabase publishableKey는 RLS로 보호되고, 카카오 키는 원래 클라이언트용 키다.)
/// 비밀로 지켜야 하는 값(Supabase service_role 키, MFDS/Vision API 키 등)은
/// Supabase Edge Functions의 시크릿으로만 보관한다.
class ApiConstants {
  ApiConstants._();

  static const String supabaseUrl = 'https://hzomhheyccapnzuwtzxh.supabase.co';
  static const String supabasePublishableKey =
      'sb_publishable_nkQI4DHl-pQ-XmPSUcmkOA_qNy2DUz-';

  static const String identifyItemEndpoint = '$supabaseUrl/functions/v1/identify-item';

  /// 카카오 디벨로퍼스에서 발급받은 JavaScript 키.
  /// kakao_map_plugin은 웹뷰 기반 지도이므로 Native 키가 아닌 JS 키를 사용한다.
  static const String kakaoJavaScriptKey = '<YOUR_KAKAO_JAVASCRIPT_KEY>';

  /// 카카오내비 딥링크(kakaonavi-sdk://) 호출에 필요한 네이티브 앱 키.
  /// JavaScript 키와는 별도로 카카오 디벨로퍼스 > 앱 키 메뉴에서 발급받는다.
  static const String kakaoNativeAppKey = '<YOUR_KAKAO_NATIVE_APP_KEY>';

  /// 네이버 지도 딥링크(nmap://)의 필수 파라미터 appname에 넣을 값.
  /// Android는 applicationId, iOS는 Bundle Identifier와 반드시 같아야 하므로
  /// 플랫폼별로 분리한다 (android/app/build.gradle.kts, ios Info.plist와 동일하게 유지할 것).
  static const String androidApplicationId = 'com.ecodisposal.eco_disposal_app';
  static const String iosBundleId = 'com.ecodisposal.ecoDisposalApp';
}
