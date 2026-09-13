import 'package:geolocator/geolocator.dart';

/// 위치 조회 과정에서 발생하는 예외 (서비스 꺼짐, 권한 거부 등).
class LocationServiceException implements Exception {
  const LocationServiceException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// GPS 권한 요청 및 현재 위치 조회를 캡슐화하는 서비스.
class LocationService {
  Future<Position> getCurrentPosition() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const LocationServiceException('위치 서비스가 꺼져 있습니다. 설정에서 켜주세요.');
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        throw const LocationServiceException('위치 권한이 거부되었습니다.');
      }
    }

    if (permission == LocationPermission.deniedForever) {
      throw const LocationServiceException(
        '위치 권한이 영구적으로 거부되었습니다. 앱 설정에서 직접 허용해 주세요.',
      );
    }

    return Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );
  }
}
