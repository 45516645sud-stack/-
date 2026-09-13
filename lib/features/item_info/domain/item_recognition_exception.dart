/// 이미지 인식 과정에서 발생하는 예외.
class ItemRecognitionException implements Exception {
  const ItemRecognitionException(this.message);

  final String message;

  @override
  String toString() => message;
}
