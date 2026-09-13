/// 길안내 목적지 (수거함) 정보.
class NavigationTarget {
  const NavigationTarget({
    required this.name,
    required this.latitude,
    required this.longitude,
  });

  final String name;
  final double latitude;
  final double longitude;
}
