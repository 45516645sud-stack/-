import 'dart:convert';
import 'dart:io' show Platform;

import '../../../core/constants/api_constants.dart';
import '../domain/navigation_app.dart';
import '../domain/navigation_target.dart';

/// 각 내비게이션 앱의 딥링크(URL Scheme) 및 앱이 없을 때 이동할 스토어 URL을 생성한다.
///
/// 참고:
/// - 카카오내비: `kakaonavi-sdk://navigate?appkey=...&apiver=1.0&param={...}`
///   (카카오 디벨로퍼스 공식 스킴, appkey는 네이티브 앱 키)
/// - T맵: iOS `tmap://route?rGoName=&rGoX=&rGoY=`, Android `tmap://route?goalname=&goalx=&goaly=`
/// - 네이버지도: `nmap://route/car?dlat=&dlng=&dname=&appname=`
///   (appname은 필수 파라미터 — 호출하는 앱의 applicationId/Bundle Identifier)
class DeeplinkUrlBuilder {
  const DeeplinkUrlBuilder();

  static const String _kakaoNaviIosStoreUrl = 'https://apps.apple.com/kr/app/id417698849';
  static const String _kakaoNaviAndroidPackage = 'com.locnall.KimGiSa';
  static const String _tmapIosStoreUrl = 'https://apps.apple.com/kr/app/id431589174';
  static const String _tmapAndroidPackage = 'com.skt.tmap.ku';
  static const String _naverMapIosStoreUrl = 'https://apps.apple.com/kr/app/id311867728';
  static const String _naverMapAndroidPackage = 'com.nhn.android.nmap';

  Uri appUri(NavigationApp app, NavigationTarget target) {
    switch (app) {
      case NavigationApp.kakaoNavi:
        return _kakaoNaviUri(target);
      case NavigationApp.tmap:
        return _tmapUri(target);
      case NavigationApp.naverMap:
        return _naverMapUri(target);
    }
  }

  /// 대상 앱이 설치되어 있지 않을 때 이동할 스토어 페이지.
  Uri storeUri(NavigationApp app) {
    switch (app) {
      case NavigationApp.kakaoNavi:
        return Platform.isIOS
            ? Uri.parse(_kakaoNaviIosStoreUrl)
            : Uri.parse('https://play.google.com/store/apps/details?id=$_kakaoNaviAndroidPackage');
      case NavigationApp.tmap:
        return Platform.isIOS
            ? Uri.parse(_tmapIosStoreUrl)
            : Uri.parse('https://play.google.com/store/apps/details?id=$_tmapAndroidPackage');
      case NavigationApp.naverMap:
        return Platform.isIOS
            ? Uri.parse(_naverMapIosStoreUrl)
            : Uri.parse('https://play.google.com/store/apps/details?id=$_naverMapAndroidPackage');
    }
  }

  Uri _kakaoNaviUri(NavigationTarget target) {
    final param = jsonEncode({
      'destination': {
        'name': target.name,
        'x': target.longitude,
        'y': target.latitude,
      },
      'option': {'coord_type': 'wgs84'},
    });

    return Uri.parse(
      'kakaonavi-sdk://navigate'
      '?appkey=${ApiConstants.kakaoNativeAppKey}'
      '&apiver=1.0'
      '&param=${Uri.encodeComponent(param)}',
    );
  }

  Uri _tmapUri(NavigationTarget target) {
    final encodedName = Uri.encodeComponent(target.name);
    if (Platform.isIOS) {
      return Uri.parse(
        'tmap://route?rGoName=$encodedName&rGoX=${target.longitude}&rGoY=${target.latitude}',
      );
    }
    return Uri.parse(
      'tmap://route?goalname=$encodedName&goalx=${target.longitude}&goaly=${target.latitude}',
    );
  }

  Uri _naverMapUri(NavigationTarget target) {
    final encodedName = Uri.encodeComponent(target.name);
    final appName = Platform.isIOS ? ApiConstants.iosBundleId : ApiConstants.androidApplicationId;
    final encodedAppName = Uri.encodeComponent(appName);
    return Uri.parse(
      'nmap://route/car'
      '?dlat=${target.latitude}'
      '&dlng=${target.longitude}'
      '&dname=$encodedName'
      '&appname=$encodedAppName',
    );
  }
}
