import { ItemCategory } from "./types.ts";

// Vision API가 반환하는 라벨 문구는 영문이며 대소문자가 섞여 있어 소문자로 비교한다.
const BATTERY_LABEL_KEYWORDS = [
  "battery",
  "batteries",
  "cylinder",
  "electronic component",
  "battery charger",
];

const PILL_LABEL_KEYWORDS = [
  "pill",
  "tablet",
  "capsule",
  "medication",
  "medicine",
  "pharmaceutical drug",
  "pharmaceutical",
];

/**
 * 범용 Vision API 라벨 인식으로 사진이 "약"인지 "건전지"인지 판별한다.
 * 전용 학습 모델이 아니라 일반 라벨의 키워드 매칭이라 정확도에 한계가 있다.
 * 오인식이 잦으면 커스텀 분류 모델로 교체할 것.
 */
export function classifyCategory(labels: string[]): ItemCategory {
  if (labels.some((label) => BATTERY_LABEL_KEYWORDS.some((keyword) => label.includes(keyword)))) {
    return "battery";
  }

  if (labels.some((label) => PILL_LABEL_KEYWORDS.some((keyword) => label.includes(keyword)))) {
    return "pill";
  }

  return "unknown";
}
