import 'package:flutter/material.dart';

import '../../../services/deeplink_service.dart';
import '../domain/navigation_app.dart';
import '../domain/navigation_target.dart';

/// 목적지로 길안내를 시작할 내비게이션 앱(카카오내비/T맵)을 고르는 바텀시트.
Future<void> showNavigationAppPicker(BuildContext context, NavigationTarget target) {
  return showModalBottomSheet(
    context: context,
    builder: (_) => _NavigationAppPickerSheet(target: target),
  );
}

class _NavigationAppPickerSheet extends StatefulWidget {
  const _NavigationAppPickerSheet({required this.target});

  final NavigationTarget target;

  @override
  State<_NavigationAppPickerSheet> createState() => _NavigationAppPickerSheetState();
}

class _NavigationAppPickerSheetState extends State<_NavigationAppPickerSheet> {
  final DeeplinkService _deeplinkService = DeeplinkService();
  bool _isLaunching = false;

  Future<void> _launch(NavigationApp app) async {
    setState(() => _isLaunching = true);
    try {
      await _deeplinkService.launch(app, widget.target);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _isLaunching = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${widget.target.name}(으)로 길안내',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            for (final app in NavigationApp.values)
              ListTile(
                leading: const Icon(Icons.navigation_outlined),
                title: Text(app.label),
                enabled: !_isLaunching,
                trailing: _isLaunching ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ) : null,
                onTap: () => _launch(app),
              ),
          ],
        ),
      ),
    );
  }
}
