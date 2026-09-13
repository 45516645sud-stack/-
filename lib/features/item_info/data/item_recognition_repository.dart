import 'dart:convert';
import 'dart:io';

import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:http/http.dart' as http;

import '../../../core/constants/api_constants.dart';
import '../domain/item_model.dart';
import '../domain/item_recognition_exception.dart';

/// 촬영된 이미지를 서버로 보내 물품을 식별하는 리포지토리.
/// UI 레이어는 이 인터페이스에만 의존하므로, 추후 온디바이스 모델(TFLite)로
/// 교체하더라도 화면 코드를 바꿀 필요가 없다.
abstract class ItemRecognitionRepository {
  Future<ItemModel> identify(File image);
}

/// Cloud Functions의 identifyItem 엔드포인트를 호출하는 구현체.
/// 서버 쪽에서 이미지 분류(약/건전지) 후, 약이면 식약처 낱알식별 API를
/// 조회하고 건전지면 고정 안내 데이터를 반환한다.
class HttpItemRecognitionRepository implements ItemRecognitionRepository {
  HttpItemRecognitionRepository({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  @override
  Future<ItemModel> identify(File image) async {
    final uri = Uri.parse(ApiConstants.identifyItemEndpoint);
    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('image', image.path));

    final appCheckToken = await FirebaseAppCheck.instance.getToken();
    if (appCheckToken != null) {
      request.headers['X-Firebase-AppCheck'] = appCheckToken;
    }

    try {
      final streamedResponse = await _client.send(request).timeout(
            const Duration(seconds: 20),
          );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 401) {
        throw const ItemRecognitionException(
          '보안 인증에 실패했습니다. 앱을 최신 버전으로 업데이트하거나 다시 설치해 주세요.',
        );
      }

      if (response.statusCode != 200) {
        throw ItemRecognitionException(
          '인식 서버 오류가 발생했습니다. (코드: ${response.statusCode})',
        );
      }

      final body = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;

      if (body['matched'] == false) {
        final category = body['category'] as String?;
        final message = switch (category) {
          'pill' => '알약 각인이 잘 보이도록 가까이서 다시 촬영해 주세요.',
          'battery' => '건전지 정보를 확인하지 못했습니다. 다시 촬영해 주세요.',
          _ => '약 또는 건전지가 잘 보이도록 다시 촬영해 주세요.',
        };
        throw ItemRecognitionException(message);
      }

      return ItemModel.fromJson(body);
    } on ItemRecognitionException {
      rethrow;
    } on SocketException {
      throw const ItemRecognitionException('네트워크 연결을 확인해 주세요.');
    } catch (e) {
      throw ItemRecognitionException('인식 중 오류가 발생했습니다: $e');
    }
  }
}
