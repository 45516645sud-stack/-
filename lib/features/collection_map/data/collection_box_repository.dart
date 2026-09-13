import 'package:supabase_flutter/supabase_flutter.dart';

import '../domain/collection_box.dart';

abstract class CollectionBoxRepository {
  Future<List<CollectionBox>> fetchAll();
}

/// Supabase의 `collection_boxes` 테이블에서 수거함 데이터를 읽어오는 구현체.
///
/// 지금은 전체 행을 가져와 클라이언트에서 거리순 정렬한다. 수거함 데이터가
/// 전국 단위로 커지면 PostGIS(`ST_DWithin` 등) 기반 반경 쿼리로 교체해야 한다.
/// 읽기는 RLS 정책으로 누구나 가능하도록 열려 있고, 쓰기는 막혀 있다
/// (supabase/migrations 참고) — 시드 업로드는 service_role 키를 쓰는
/// 별도 스크립트로만 수행한다.
class SupabaseCollectionBoxRepository implements CollectionBoxRepository {
  SupabaseCollectionBoxRepository({SupabaseClient? client})
      : _client = client ?? Supabase.instance.client;

  final SupabaseClient _client;
  static const String _tableName = 'collection_boxes';

  @override
  Future<List<CollectionBox>> fetchAll() async {
    final rows = await _client.from(_tableName).select();
    return rows.map(CollectionBox.fromRow).toList();
  }
}
