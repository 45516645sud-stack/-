import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../../../main.dart' show availableCamerasList;
import '../../../services/camera_service.dart';
import 'photo_preview_screen.dart';
import 'widgets/capture_button.dart';
import 'widgets/permission_denied_view.dart';

enum _CameraScreenStatus { loading, permissionDenied, ready, noCameraFound, error }

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with WidgetsBindingObserver {
  final CameraService _cameraService = CameraService();

  _CameraScreenStatus _status = _CameraScreenStatus.loading;
  int _selectedCameraIndex = 0;
  bool _isCapturing = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _setUp();
  }

  Future<void> _setUp() async {
    final granted = await _cameraService.requestPermission();
    if (!granted) {
      setState(() => _status = _CameraScreenStatus.permissionDenied);
      return;
    }
    if (availableCamerasList.isEmpty) {
      setState(() => _status = _CameraScreenStatus.noCameraFound);
      return;
    }
    await _initializeCamera(_selectedCameraIndex);
  }

  Future<void> _initializeCamera(int index) async {
    try {
      await _cameraService.initialize(availableCamerasList[index]);
      if (!mounted) return;
      setState(() {
        _selectedCameraIndex = index;
        _status = _CameraScreenStatus.ready;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _status = _CameraScreenStatus.error;
        _errorMessage = e.toString();
      });
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // 앱이 백그라운드로 가면 카메라 리소스를 해제하고, 복귀 시 재초기화한다.
    if (!_cameraService.isInitialized) return;
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      _cameraService.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _initializeCamera(_selectedCameraIndex);
    }
  }

  Future<void> _onCapturePressed() async {
    if (_isCapturing) return;
    setState(() => _isCapturing = true);
    try {
      final file = await _cameraService.takePicture();
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => PhotoPreviewScreen(imagePath: file.path)),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('촬영에 실패했습니다: $e')),
      );
    } finally {
      if (mounted) setState(() => _isCapturing = false);
    }
  }

  void _onSwitchCamera() {
    if (availableCamerasList.length < 2) return;
    final nextIndex = (_selectedCameraIndex + 1) % availableCamerasList.length;
    setState(() => _status = _CameraScreenStatus.loading);
    _initializeCamera(nextIndex);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _cameraService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: switch (_status) {
          _CameraScreenStatus.loading => const Center(
              child: CircularProgressIndicator(),
            ),
          _CameraScreenStatus.permissionDenied => PermissionDeniedView(onRetry: _setUp),
          _CameraScreenStatus.noCameraFound => const Center(
              child: Text(
                '사용 가능한 카메라를 찾을 수 없습니다.',
                style: TextStyle(color: Colors.white),
              ),
            ),
          _CameraScreenStatus.error => Center(
              child: Text(
                '카메라 오류: $_errorMessage',
                style: const TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
            ),
          _CameraScreenStatus.ready => _buildCameraPreview(),
        },
      ),
    );
  }

  Widget _buildCameraPreview() {
    final controller = _cameraService.controller;
    if (controller == null || !controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        CameraPreview(controller),
        _buildTopBar(),
        _buildBottomBar(),
      ],
    );
  }

  Widget _buildTopBar() {
    return Align(
      alignment: Alignment.topCenter,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              '폐의약품 / 폐건전지를 촬영해 주세요',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                shadows: [Shadow(blurRadius: 6, color: Colors.black)],
              ),
            ),
            if (availableCamerasList.length > 1)
              IconButton(
                onPressed: _onSwitchCamera,
                icon: const Icon(Icons.cameraswitch, color: Colors.white),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomBar() {
    return Align(
      alignment: Alignment.bottomCenter,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 32),
        child: CaptureButton(
          isBusy: _isCapturing,
          onPressed: _onCapturePressed,
        ),
      ),
    );
  }
}
