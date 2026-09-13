interface NamedColor {
  name: string;
  rgb: [number, number, number];
}

// 식약처 낱알식별 API의 color_class1 파라미터가 쓰는 한글 색상 이름과
// 그 색을 대표하는 RGB 값. 실제 알약 색상을 이 팔레트에서 가장 가까운
// 색으로 근사(최근접 이웃)한다 — 정밀한 색상 분류가 아닌 검색 힌트 용도.
const KOREAN_COLOR_PALETTE: NamedColor[] = [
  { name: "하양", rgb: [255, 255, 255] },
  { name: "노랑", rgb: [255, 221, 51] },
  { name: "주황", rgb: [255, 140, 0] },
  { name: "분홍", rgb: [255, 182, 193] },
  { name: "빨강", rgb: [220, 20, 60] },
  { name: "갈색", rgb: [139, 69, 19] },
  { name: "연두", rgb: [173, 255, 47] },
  { name: "초록", rgb: [34, 139, 34] },
  { name: "청색", rgb: [30, 144, 255] },
  { name: "남색", rgb: [25, 25, 112] },
  { name: "보라", rgb: [138, 43, 226] },
  { name: "회색", rgb: [128, 128, 128] },
  { name: "검정", rgb: [30, 30, 30] },
];

interface Rgb {
  red?: number | null;
  green?: number | null;
  blue?: number | null;
}

export function nearestKoreanColorName(color: Rgb): string | undefined {
  if (color.red == null || color.green == null || color.blue == null) return undefined;

  let bestName: string | undefined;
  let bestDistance = Infinity;

  for (const candidate of KOREAN_COLOR_PALETTE) {
    const [r, g, b] = candidate.rgb;
    const distance = (color.red - r) ** 2 + (color.green - g) ** 2 + (color.blue - b) ** 2;
    if (distance < bestDistance) {
      bestDistance = distance;
      bestName = candidate.name;
    }
  }

  return bestName;
}
