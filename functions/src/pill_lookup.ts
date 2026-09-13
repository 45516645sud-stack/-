import axios from "axios";
import { defineSecret } from "firebase-functions/params";
import { IdentifyResult } from "./types";

// 공공데이터포털 "의약품 낱알식별정보" 서비스키. `firebase functions:secrets:set MFDS_API_KEY`로 등록한다.
export const mfdsApiKey = defineSecret("MFDS_API_KEY");

const MFDS_ENDPOINT =
  "http://apis.data.go.kr/1471000/MdcinGrnIdntfcInfoService02/getMdcinGrnIdntfcInfoList02";

interface PillFeatures {
  /** 알약에 각인된 문자/기호 (앞면). OCR 결과. */
  printFront?: string;
  drugShape?: string;
  colorClass1?: string;
}

/**
 * TODO: 실제 이미지 분석 연동 지점.
 * 지금은 자리표시자로 빈 특징을 반환한다. 실서비스에서는 여기서
 * Vision API(각인 OCR) + 모양/색상 분류 모델 결과를 채워 넣어야 한다.
 */
export async function extractPillFeatures(_imageBuffer: Buffer): Promise<PillFeatures> {
  return {};
}

export async function lookupPill(features: PillFeatures): Promise<IdentifyResult> {
  const response = await axios.get(MFDS_ENDPOINT, {
    params: {
      serviceKey: mfdsApiKey.value(),
      type: "json",
      numOfRows: 1,
      pageNo: 1,
      print_front: features.printFront,
      drug_shape: features.drugShape,
      color_class1: features.colorClass1,
    },
    timeout: 8000,
  });

  const item = response.data?.body?.items?.[0];
  if (!item) {
    return {
      matched: false,
      category: "pill",
      name: "",
      description: "",
      disposalSteps: [],
      precautions: [],
    };
  }

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
