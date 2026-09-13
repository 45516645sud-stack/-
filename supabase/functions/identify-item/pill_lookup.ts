import { nearestKoreanColorName } from "./color_map.ts";
import { IdentifyResult } from "./types.ts";
import { VisionAnnotations } from "./vision.ts";

const MFDS_ENDPOINT =
  "http://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService02/getMdcinGrnIdntfcInfoList02";

interface PillFeatures {
  /** 알약에 각인된 문자/기호 (앞면). OCR 결과. */
  printFront?: string;
  colorClass1?: string;
}

/**
 * Vision API 결과에서 각인 문자(OCR)와 대표 색상을 추출한다.
 *
 * 한계: 알약 각인은 매우 작고 대비가 낮아 범용 OCR 정확도가 떨어질 수 있다.
 * 모양(drug_shape)은 별도 분류 모델 없이는 신뢰도 있게 추정하기 어려워
 * 이번 연동에서는 시도하지 않는다.
 */
export function extractPillFeatures(annotations: VisionAnnotations): PillFeatures {
  const printFront = normalizeImprintText(annotations.ocrText);
  const colorClass1 = annotations.dominantColor
    ? nearestKoreanColorName(annotations.dominantColor)
    : undefined;

  return {
    printFront: printFront || undefined,
    colorClass1,
  };
}

/** 각인은 보통 짧은 영숫자/한글 조합이므로 OCR 결과에서 공백·기호를 제거하고 앞부분만 취한다. */
function normalizeImprintText(text: string): string {
  return text
    .replace(/\s+/g, "")
    .replace(/[^A-Za-z0-9가-힣]/g, "")
    .toUpperCase()
    .slice(0, 10);
}

export async function lookupPill(features: PillFeatures, mfdsApiKey: string): Promise<IdentifyResult> {
  if (!features.printFront) {
    return buildNoMatch();
  }

  // 각인+색상으로 먼저 검색하고, 결과가 없으면 색상 조건을 빼고 각인만으로 재시도한다.
  const withColor = await queryMfds(mfdsApiKey, {
    print_front: features.printFront,
    color_class1: features.colorClass1,
  });
  if (withColor) return withColor;

  if (features.colorClass1) {
    const withoutColor = await queryMfds(mfdsApiKey, { print_front: features.printFront });
    if (withoutColor) return withoutColor;
  }

  return buildNoMatch();
}

async function queryMfds(
  mfdsApiKey: string,
  params: { print_front: string; color_class1?: string },
): Promise<IdentifyResult | null> {
  const url = new URL(MFDS_ENDPOINT);
  url.searchParams.set("serviceKey", mfdsApiKey);
  url.searchParams.set("type", "json");
  url.searchParams.set("numOfRows", "1");
  url.searchParams.set("pageNo", "1");
  url.searchParams.set("print_front", params.print_front);
  if (params.color_class1) {
    url.searchParams.set("color_class1", params.color_class1);
  }

  const response = await fetch(url, { signal: AbortSignal.timeout(8000) });
  if (!response.ok) {
    throw new Error(`식약처 API 오류 (${response.status})`);
  }

  const data = await response.json();
  const item = data?.body?.items?.[0];
  if (!item) return null;

  return {
    matched: true,
    category: "pill",
    name: item.ITEM_NAME ?? "이름 미상 의약품",
    description: `${item.ENTP_NAME ?? ""} · ${item.CLASS_NAME ?? ""}`.trim(),
    disposalSteps: [
      "남거나 유통기한이 지난 약은 일반 쓰레기·하수구에 버리지 마세요.",
      "포장(알루미늄, 병 등)은 제거하고 알약만 모아 배출하세요.",
      "가까운 약국이나 보건소, 주민센터의 폐의약품 수거함에 배출하세요.",
    ],
    precautions: [
      "물에 녹여서 버리면 수질 오염의 원인이 됩니다.",
      "자녀나 반려동물의 손이 닿지 않는 곳에 보관 후 배출하세요.",
    ],
    imageUrl: item.ITEM_IMAGE ?? undefined,
    confidence: undefined,
  };
}

function buildNoMatch(): IdentifyResult {
  return {
    matched: false,
    category: "pill",
    name: "",
    description: "",
    disposalSteps: [],
    precautions: [],
  };
}
