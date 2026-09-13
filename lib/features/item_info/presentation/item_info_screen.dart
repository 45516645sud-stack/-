import 'dart:io';

import 'package:flutter/material.dart';

import '../../collection_map/presentation/map_screen.dart';
import '../data/item_recognition_repository.dart';
import '../domain/item_category.dart';
import '../domain/item_model.dart';
import '../domain/item_recognition_exception.dart';

/// 촬영된 사진을 인식 서버로 보내고, 결과(이름/폐기방법/주의사항)를 보여주는 화면.
class ItemInfoScreen extends StatefulWidget {
  ItemInfoScreen({
    super.key,
    required this.imagePath,
    ItemRecognitionRepository? repository,
  }) : repository = repository ?? HttpItemRecognitionRepository();

  final String imagePath;
  final ItemRecognitionRepository repository;

  @override
  State<ItemInfoScreen> createState() => _ItemInfoScreenState();
}

class _ItemInfoScreenState extends State<ItemInfoScreen> {
  late Future<ItemModel> _future;

  @override
  void initState() {
    super.initState();
    _future = _identify();
  }

  Future<ItemModel> _identify() {
    return widget.repository.identify(File(widget.imagePath));
  }

  void _retry() {
    setState(() => _future = _identify());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('인식 결과')),
      body: FutureBuilder<ItemModel>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return _buildLoading();
          }
          if (snapshot.hasError) {
            return _buildError(snapshot.error);
          }
          return _buildResult(snapshot.data!);
        },
      ),
    );
  }

  Widget _buildLoading() {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('사진을 분석하고 있어요...'),
        ],
      ),
    );
  }

  Widget _buildError(Object? error) {
    final message = error is ItemRecognitionException ? error.message : '알 수 없는 오류가 발생했습니다.';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.redAccent),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('다시 촬영'),
                ),
                const SizedBox(width: 12),
                FilledButton(onPressed: _retry, child: const Text('재시도')),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResult(ItemModel item) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(
                  File(widget.imagePath),
                  width: 88,
                  height: 88,
                  fit: BoxFit.cover,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Chip(label: Text(item.category.label)),
                    const SizedBox(height: 6),
                    Text(item.name, style: Theme.of(context).textTheme.titleLarge),
                  ],
                ),
              ),
            ],
          ),
          if (item.description.isNotEmpty) ...[
            const SizedBox(height: 20),
            Text(item.description, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 24),
          _buildListSection(
            context,
            icon: Icons.recycling,
            title: '올바른 폐기 방법',
            items: item.disposalSteps,
          ),
          const SizedBox(height: 20),
          _buildListSection(
            context,
            icon: Icons.warning_amber_rounded,
            title: '주의사항',
            items: item.precautions,
            iconColor: Colors.orange,
          ),
          const SizedBox(height: 32),
          FilledButton.icon(
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => MapScreen(categoryFilter: item.category),
                ),
              );
            },
            icon: const Icon(Icons.map_outlined),
            label: const Text('가까운 수거함 찾기'),
          ),
        ],
      ),
    );
  }

  Widget _buildListSection(
    BuildContext context, {
    required IconData icon,
    required String title,
    required List<String> items,
    Color? iconColor,
  }) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 20, color: iconColor),
            const SizedBox(width: 8),
            Text(title, style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
        const SizedBox(height: 8),
        ...items.map(
          (text) => Padding(
            padding: const EdgeInsets.only(bottom: 6, left: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('•  '),
                Expanded(child: Text(text)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
