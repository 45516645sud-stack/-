import { ItemCategory } from "./types";

/**
 * TODO: 실제 이미지 분류 모델/API 연동 지점.
 * 예) 자체 학습한 TFLite/Vertex AI 모델, 혹은 범용 Vision API에 커스텀 라벨 매핑.
 * 지금은 항상 "pill"을 반환하는 자리표시자이며, 추후 별도 단계에서 교체한다.
 */
export async function classifyImage(_imageBuffer: Buffer): Promise<ItemCategory> {
  return "pill";
}
