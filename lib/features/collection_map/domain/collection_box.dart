import '../../item_info/domain/item_category.dart';

/// 폐의약품/폐건전지 수거함 한 곳의 정보.
class CollectionBox {
  const CollectionBox({
    required this.id,
    required this.name,
    required this.address,
    required this.latitude,
    required this.longitude,
    required this.categories,
  });

  final String id;
  final String name;
  final String address;
  final double latitude;
  final double longitude;

  /// 이 수거함이 받는 품목 종류. 예: [pill], [battery], [pill, battery].
  final List<ItemCategory> categories;

  factory CollectionBox.fromFirestore(String id, Map<String, dynamic> data) {
    return CollectionBox(
      id: id,
      name: data['name'] as String? ?? '수거함',
      address: data['address'] as String? ?? '',
      latitude: (data['latitude'] as num).toDouble(),
      longitude: (data['longitude'] as num).toDouble(),
      categories: ((data['categories'] as List<dynamic>?) ?? const ['pill', 'battery'])
          .map((e) => ItemCategory.fromApiValue(e as String))
          .toList(),
    );
  }
}
