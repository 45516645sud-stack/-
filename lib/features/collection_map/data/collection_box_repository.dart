import 'package:cloud_firestore/cloud_firestore.dart';

import '../domain/collection_box.dart';

abstract class CollectionBoxRepository {
  Future<List<CollectionBox>> fetchAll();
}

/// Firestore의 `collection_boxes` 컬렉션에서 수거함 데이터를 읽어오는 구현체.
///
/// 지금은 전체 문서를 가져와 클라이언트에서 거리순 정렬한다. 수거함 데이터가
/// 전국 단위로 커지면 geohash 기반 반경 쿼리(geoflutterfire 등)로 교체해야 한다.
class FirestoreCollectionBoxRepository implements CollectionBoxRepository {
  FirestoreCollectionBoxRepository({FirebaseFirestore? firestore})
      : _firestore = firestore ?? FirebaseFirestore.instance;

  final FirebaseFirestore _firestore;
  static const String _collectionName = 'collection_boxes';

  @override
  Future<List<CollectionBox>> fetchAll() async {
    final snapshot = await _firestore.collection(_collectionName).get();
    return snapshot.docs
        .map((doc) => CollectionBox.fromFirestore(doc.id, doc.data()))
        .toList();
  }
}
