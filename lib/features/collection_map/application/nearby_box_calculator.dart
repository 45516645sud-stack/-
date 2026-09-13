import 'package:geolocator/geolocator.dart';

import '../../item_info/domain/item_category.dart';
import '../domain/collection_box.dart';

/// 거리 계산 결과를 담는 값 객체.
class NearbyBox {
  const NearbyBox({required this.box, required this.distanceMeters});

  final CollectionBox box;
  final double distanceMeters;

  String get distanceLabel {
    if (distanceMeters < 1000) return '${distanceMeters.round()}m';
    return '${(distanceMeters / 1000).toStringAsFixed(1)}km';
  }
}

/// 현재 위치 기준으로 수거함 목록을 필터링/정렬하는 로직.
class NearbyBoxCalculator {
  const NearbyBoxCalculator();

  List<NearbyBox> sortByDistance({
    required List<CollectionBox> boxes,
    required double currentLatitude,
    required double currentLongitude,
    ItemCategory? categoryFilter,
    double? maxDistanceMeters,
  }) {
    final filtered = categoryFilter == null
        ? boxes
        : boxes.where((box) => box.categories.contains(categoryFilter)).toList();

    final withDistance = filtered
        .map(
          (box) => NearbyBox(
            box: box,
            distanceMeters: Geolocator.distanceBetween(
              currentLatitude,
              currentLongitude,
              box.latitude,
              box.longitude,
            ),
          ),
        )
        .where((nb) => maxDistanceMeters == null || nb.distanceMeters <= maxDistanceMeters)
        .toList();

    withDistance.sort((a, b) => a.distanceMeters.compareTo(b.distanceMeters));
    return withDistance;
  }
}
