/**
 * Firestore의 `collection_boxes` 컬렉션에 수거함 데이터를 일괄 업로드하는 스크립트.
 *
 * 사용법:
 *   1. Firebase 콘솔 > 프로젝트 설정 > 서비스 계정에서 비공개 키(JSON) 발급
 *   2. GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json npm run seed
 *      (입력 JSON 경로를 바꾸려면: npm run seed -- ./seed-data/my_data.json)
 *
 * 입력 JSON은 lib/features/collection_map/domain/collection_box.dart의
 * CollectionBox.fromFirestore가 기대하는 필드와 동일한 구조여야 한다:
 * { id, name, address, latitude, longitude, categories: ("pill"|"battery")[] }
 *
 * 실제 서비스용 데이터는 공공데이터포털의 지자체별 "폐의약품 수거함" /
 * "폐건전지 수거함 설치 현황" 데이터셋을 내려받아 위 구조로 매핑해서 사용한다.
 */
import * as admin from "firebase-admin";
import * as fs from "fs";
import * as path from "path";

interface SeedCollectionBox {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  categories: ("pill" | "battery")[];
}

const DEFAULT_DATA_PATH = path.resolve(__dirname, "../../seed-data/collection_boxes.sample.json");

async function main() {
  const dataPath = process.argv[2] ? path.resolve(process.cwd(), process.argv[2]) : DEFAULT_DATA_PATH;

  const raw = fs.readFileSync(dataPath, "utf-8");
  const boxes = JSON.parse(raw) as SeedCollectionBox[];
  validate(boxes);

  admin.initializeApp({ credential: admin.credential.applicationDefault() });
  const firestore = admin.firestore();

  const batch = firestore.batch();
  for (const box of boxes) {
    const { id, ...data } = box;
    batch.set(firestore.collection("collection_boxes").doc(id), data);
  }
  await batch.commit();

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
  process.exit(1);
});
