import 'package:flutter/material.dart';

import 'features/camera/presentation/camera_screen.dart';

class EcoDisposalApp extends StatelessWidget {
  const EcoDisposalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '폐의약품·폐건전지 수거함 안내',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF2E7D32),
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const CameraScreen(),
    );
  }
}
