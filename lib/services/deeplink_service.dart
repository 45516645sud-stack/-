import 'package:url_launcher/url_launcher.dart';

import '../features/navigation_deeplink/data/deeplink_url_builder.dart';
import '../features/navigation_deeplink/domain/navigation_app.dart';
import '../features/navigation_deeplink/domain/navigation_target.dart';

class DeeplinkLaunchException implements Exception {
  const DeeplinkLaunchException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// 목적지로 카카오내비/T맵 딥링크를 실행하는 서비스.
/// 대상 앱이 설치되어 있지 않으면 스토어 페이지로 대신 이동한다.
class DeeplinkService {
  DeeplinkService({DeeplinkUrlBuilder? urlBuilder}) : _urlBuilder = urlBuilder ?? const DeeplinkUrlBuilder();

  final DeeplinkUrlBuilder _urlBuilder;

  Future<void> launch(NavigationApp app, NavigationTarget target) async {
    final appUri = _urlBuilder.appUri(app, target);
    if (await _tryLaunch(appUri)) return;

    final storeUri = _urlBuilder.storeUri(app);
    if (await _tryLaunch(storeUri)) return;

    throw DeeplinkLaunchException('${app.label}을(를) 열 수 없습니다.');
  }

  Future<bool> _tryLaunch(Uri uri) async {
    try {
      return await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      return false;
    }
  }
}
