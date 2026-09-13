import { IdentifyResult } from "./types";

// 건전지는 개별 API 조회가 필요 없어 고정 안내 데이터를 사용한다.
export function buildBatteryResult(): IdentifyResult {
  return {
    matched: true,
    category: "battery",
    name: "폐건전지",
    description: "일반 건전지(1차전지)로 분류됩니다. 절대 일반 쓰레기와 함께 버리지 마세요.",
    disposalSteps: [
      "단자(양 끝 금속 부분)에 테이프를 붙여 합선을 방지하세요.",
      "아파트 단지나 주민센터에 비치된 폐건전지 전용 수거함에 배출하세요.",
      "여러 개를 모아서 한 번에 배출하면 더 좋습니다.",
    ],
    precautions: [
      "액이 새거나 부풀어 오른 건전지는 밀봉된 봉투에 넣어 배출하세요.",
      "고온 다습한 곳에 보관하지 마세요.",
      "리튬이온 배터리(휴대폰, 보조배터리 등)는 별도의 폐전지 수거함이 아닌 소형가전 수거함으로 배출해야 합니다.",
    ],
  };
}
