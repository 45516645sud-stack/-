import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';

/// CameraController 생명주기와 권한 요청을 캡슐화하는 서비스.
/// CameraScreen은 이 서비스를 통해서만 카메라를 다룬다.
class CameraService {
  CameraController? _controller;

  CameraController? get controller => _controller;
  bool get isInitialized => _controller?.value.isInitialized ?? false;

  /// 카메라 권한을 요청하고 결과를 반환한다.
  Future<bool> requestPermission() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  /// 주어진 카메라로 컨트롤러를 초기화한다.
  Future<void> initialize(CameraDescription description) async {
    final controller = CameraController(
      description,
      ResolutionPreset.high,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );
    _controller = controller;
    await controller.initialize();
  }

  /// 사진을 촬영하고 파일 경로를 반환한다.
  Future<XFile> takePicture() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      throw StateError('카메라가 초기화되지 않았습니다.');
    }
    if (controller.value.isTakingPicture) {
      throw StateError('이미 촬영 중입니다.');
    }
    return controller.takePicture();
  }

  Future<void> dispose() async {
    await _controller?.dispose();
    _controller = null;
  }
}
