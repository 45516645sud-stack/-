import 'dart:io';

import 'package:flutter/material.dart';

/// 촬영한 사진을 확인하고, 재촬영하거나 인식 단계로 넘길지 선택하는 화면.
class PhotoPreviewScreen extends StatelessWidget {
  const PhotoPreviewScreen({super.key, required this.imagePath});

  final String imagePath;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.file(File(imagePath), fit: BoxFit.contain),
            Align(
              alignment: Alignment.bottomCenter,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.refresh),
                      label: const Text('다시 촬영'),
                    ),
                    FilledButton.icon(
                      onPressed: () {
                        // TODO(2단계): 이 사진을 식약처 알약 식별 API로 전송하고
                        // item_info 화면으로 인식 결과를 넘기는 로직을 연결한다.
                      },
                      icon: const Icon(Icons.check),
                      label: const Text('이 사진 사용'),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
