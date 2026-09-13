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

  /// Supabase `collection_boxes` 테이블의 한 행(Map)을 도메인 모델로 변환한다.
  factory CollectionBox.fromRow(Map<String, dynamic> row) {
    return CollectionBox(
      id: row['id'] as String,
      name: row['name'] as String? ?? '수거함',
      address: row['address'] as String? ?? '',
      latitude: (row['latitude'] as num).toDouble(),
      longitude: (row['longitude'] as num).toDouble(),
      categories: ((row['categories'] as List<dynamic>?) ?? const ['pill', 'battery'])
          .map((e) => ItemCategory.fromApiValue(e as String))
          .toList(),
    );
  }
}
