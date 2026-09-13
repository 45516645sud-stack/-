import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:kakao_map_plugin/kakao_map_plugin.dart';

import '../../../services/location_service.dart';
import '../../item_info/domain/item_category.dart';
import '../../navigation_deeplink/domain/navigation_target.dart';
import '../../navigation_deeplink/presentation/navigation_app_picker.dart';
import '../application/nearby_box_calculator.dart';
import '../data/collection_box_repository.dart';

enum _MapScreenStatus { loading, error, ready }

/// 현재 위치 기반으로 가장 가까운 폐의약품/폐건전지 수거함을 지도에 표시하는 화면.
class MapScreen extends StatefulWidget {
  const MapScreen({super.key, this.categoryFilter});

  /// item_info 화면에서 넘어온 경우, 해당 카테고리를 받는 수거함만 보여준다.
  final ItemCategory? categoryFilter;

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  static const double _searchRadiusMeters = 5000;

  final LocationService _locationService = LocationService();
  final CollectionBoxRepository _boxRepository = FirestoreCollectionBoxRepository();
  final NearbyBoxCalculator _calculator = const NearbyBoxCalculator();

  _MapScreenStatus _status = _MapScreenStatus.loading;
  String? _errorMessage;
  Position? _currentPosition;
  List<NearbyBox> _nearbyBoxes = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _status = _MapScreenStatus.loading);
    try {
      final position = await _locationService.getCurrentPosition();
      final boxes = await _boxRepository.fetchAll();
      final nearby = _calculator
          .sortByDistance(
            boxes: boxes,
            currentLatitude: position.latitude,
            currentLongitude: position.longitude,
            categoryFilter: widget.categoryFilter,
            maxDistanceMeters: _searchRadiusMeters,
          )
          .take(20)
          .toList();

      if (!mounted) return;
      setState(() {
        _currentPosition = position;
        _nearbyBoxes = nearby;
        _status = _MapScreenStatus.ready;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _status = _MapScreenStatus.error;
        _errorMessage = e is LocationServiceException ? e.message : '수거함 정보를 불러오지 못했습니다.\n($e)';
      });
    }
  }

  void _onMarkerTap(String markerId, LatLng latLng, int zoomLevel) {
    final matches = _nearbyBoxes.where((nb) => nb.box.id == markerId);
    if (matches.isEmpty) return;
    _showBoxSheet(matches.first);
  }

  void _showBoxSheet(NearbyBox nearbyBox) {
    final box = nearbyBox.box;
    // 길찾기 시트를 열 때 사용할 MapScreen 자체의 context (바텀시트가 닫혀도 유효함).
    final screenContext = context;
    showModalBottomSheet(
      context: context,
      builder: (context) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(box.name, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(box.address, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.directions_walk, size: 18),
                const SizedBox(width: 4),
                Text('현재 위치에서 ${nearbyBox.distanceLabel}'),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              children: box.categories.map((c) => Chip(label: Text(c.label))).toList(),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () {
                  Navigator.of(context).pop();
                  showNavigationAppPicker(
                    screenContext,
                    NavigationTarget(
                      name: box.name,
                      latitude: box.latitude,
                      longitude: box.longitude,
                    ),
                  );
                },
                icon: const Icon(Icons.navigation),
                label: const Text('길찾기'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('내 주변 수거함')),
      body: switch (_status) {
        _MapScreenStatus.loading => const Center(child: CircularProgressIndicator()),
        _MapScreenStatus.error => _buildError(),
        _MapScreenStatus.ready => _buildMap(),
      },
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.location_off, size: 48, color: Colors.redAccent),
            const SizedBox(height: 16),
            Text(_errorMessage ?? '알 수 없는 오류가 발생했습니다.', textAlign: TextAlign.center),
            const SizedBox(height: 20),
            FilledButton(onPressed: _load, child: const Text('다시 시도')),
          ],
        ),
      ),
    );
  }

  Widget _buildMap() {
    final position = _currentPosition!;
    final markers = <Marker>[
      Marker(
        markerId: 'current_location',
        latLng: LatLng(position.latitude, position.longitude),
        title: '내 위치',
      ),
      for (final nb in _nearbyBoxes)
        Marker(
          markerId: nb.box.id,
          latLng: LatLng(nb.box.latitude, nb.box.longitude),
          title: nb.box.name,
        ),
    ];

    return Stack(
      children: [
        KakaoMap(
          onMapCreated: (controller) {},
          center: LatLng(position.latitude, position.longitude),
          currentLevel: 4,
          markers: markers,
          onMarkerTap: _onMarkerTap,
        ),
        if (_nearbyBoxes.isEmpty)
          Positioned(
            top: 16,
            left: 16,
            right: 16,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  '반경 ${(_searchRadiusMeters / 1000).toStringAsFixed(0)}km 내 등록된 수거함이 없습니다.',
                ),
              ),
            ),
          ),
      ],
    );
  }
}
