/// 인식된 폐기물 종류.
enum ItemCategory {
  pill('의약품'),
  battery('건전지'),
  unknown('알 수 없음');

  const ItemCategory(this.label);

  final String label;

  static ItemCategory fromApiValue(String? value) {
    switch (value) {
      case 'pill':
        return ItemCategory.pill;
      case 'battery':
        return ItemCategory.battery;
      default:
        return ItemCategory.unknown;
    }
  }
}
