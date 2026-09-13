import 'item_category.dart';

/// 인식된 약/건전지에 대한 정보. 식약처 API 응답 또는 건전지 고정 안내를
/// 동일한 형태로 담기 위한 도메인 모델.
class ItemModel {
  const ItemModel({
    required this.category,
    required this.name,
    required this.description,
    required this.disposalSteps,
    required this.precautions,
    this.imageUrl,
    this.confidence,
  });

  final ItemCategory category;
  final String name;
  final String description;

  /// 올바른 폐기 방법 (단계별 안내 문구).
  final List<String> disposalSteps;

  /// 주의사항.
  final List<String> precautions;

  /// 식약처 낱알식별 API가 제공하는 실물 이미지 URL (있는 경우).
  final String? imageUrl;

  /// 인식 신뢰도(0.0 ~ 1.0). 없으면 null.
  final double? confidence;

  factory ItemModel.fromJson(Map<String, dynamic> json) {
    return ItemModel(
      category: ItemCategory.fromApiValue(json['category'] as String?),
      name: json['name'] as String? ?? '이름을 확인할 수 없음',
      description: json['description'] as String? ?? '',
      disposalSteps: (json['disposalSteps'] as List<dynamic>? ?? const [])
          .map((e) => e.toString())
          .toList(),
      precautions: (json['precautions'] as List<dynamic>? ?? const [])
          .map((e) => e.toString())
          .toList(),
      imageUrl: json['imageUrl'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
    );
  }
}
