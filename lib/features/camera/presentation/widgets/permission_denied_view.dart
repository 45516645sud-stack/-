import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

/// 카메라 권한이 거부되었을 때 보여주는 안내 화면.
class PermissionDeniedView extends StatelessWidget {
  const PermissionDeniedView({super.key, required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.no_photography, color: Colors.white54, size: 48),
            const SizedBox(height: 16),
            const Text(
              '약이나 건전지를 인식하려면\n카메라 권한이 필요합니다.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white),
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: onRetry,
              child: const Text('권한 다시 요청'),
            ),
            TextButton(
              onPressed: openAppSettings,
              child: const Text('앱 설정에서 직접 허용', style: TextStyle(color: Colors.white70)),
            ),
          ],
        ),
      ),
    );
  }
}
