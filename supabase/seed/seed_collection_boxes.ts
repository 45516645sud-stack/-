/**
 * Supabase의 `collection_boxes` 테이블에 수거함 데이터를 일괄 업로드하는 스크립트.
 * RLS를 우회해야 하므로 service_role(또는 새 secret) 키가 필요하다 —
 * 절대 클라이언트 앱이나 커밋된 파일에 넣지 말 것.
 *
 * 사용법 (Deno):
 *   SUPABASE_URL=https://xxxx.supabase.co \
 *   SUPABASE_SERVICE_ROLE_KEY=... \
 *   deno run --allow-net --allow-read --allow-env supabase/seed/seed_collection_boxes.ts
 *
 *   입력 JSON 경로를 바꾸려면 마지막에 인자로 전달:
 *   ... deno run ... supabase/seed/seed_collection_boxes.ts ./my_data.json
 *
 * 입력 JSON 구조 (lib/features/collection_map/domain/collection_box.dart의
 * CollectionBox.fromRow와 대응):
 * { id, name, address, latitude, longitude, categories: ("pill"|"battery")[] }[]
 *
 * 실제 서비스용 데이터는 공공데이터포털의 지자체별 "폐의약품 수거함" /
 * "폐건전지 수거함 설치 현황" 데이터셋을 내려받아 위 구조로 매핑해서 사용한다.
 */
import { createClient } from "jsr:@supabase/supabase-js@2";

interface SeedCollectionBox {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  categories: ("pill" | "battery")[];
}

const DEFAULT_DATA_PATH = new URL("./collection_boxes.sample.json", import.meta.url);

async function main() {
  const dataPath = Deno.args[0] ?? DEFAULT_DATA_PATH;
  const raw = await Deno.readTextFile(dataPath);
  const boxes = JSON.parse(raw) as SeedCollectionBox[];
  validate(boxes);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey =
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? Deno.env.get("SUPABASE_SECRET_KEY");
  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY(또는 SUPABASE_SECRET_KEY) 환경변수가 필요합니다.");
  }

  const supabase = createClient(supabaseUrl, serviceRoleKey);
  const { error } = await supabase.from("collection_boxes").upsert(boxes);
  if (error) {
    throw new Error(`업로드 실패: ${error.message}`);
  }

  console.log(`collection_boxes에 ${boxes.length}건 업로드 완료 (${dataPath})`);
}

function validate(boxes: SeedCollectionBox[]) {
  boxes.forEach((box, index) => {
    if (!box.id || !box.name || !box.address) {
      throw new Error(`[${index}] id/name/address는 필수입니다.`);
    }
    if (typeof box.latitude !== "number" || typeof box.longitude !== "number") {
      throw new Error(`[${index}] latitude/longitude는 숫자여야 합니다.`);
    }
    if (!Array.isArray(box.categories) || box.categories.length === 0) {
      throw new Error(`[${index}] categories는 최소 1개 이상이어야 합니다.`);
    }
  });
}

main().catch((error) => {
  console.error("시드 업로드 실패:", error);
  Deno.exit(1);
});
