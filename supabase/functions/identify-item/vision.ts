// Cloud Functions(Node)에서는 @google-cloud/vision 클라이언트가 GCP 기본
// 서비스 계정(ADC)으로 인증했지만, Supabase Edge Functions(Deno)에는 그런
// 자동 인증이 없다. 대신 REST API를 API 키로 직접 호출한다.
// 키는 GCP 콘솔 > API 및 서비스 > 사용자 인증 정보에서 발급받고
// `supabase secrets set GOOGLE_VISION_API_KEY=...`로 등록한다.
const VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate";

export interface VisionAnnotations {
  /** 소문자로 정규화한 라벨 문자열 목록 (예: "pill", "battery"). */
  labels: string[];
  /** 이미지 전체에서 인식된 텍스트 (각인 후보). */
  ocrText: string;
  dominantColor?: { red: number; green: number; blue: number };
}

/**
 * 라벨 인식(약/건전지 판별) + 텍스트 인식(각인 OCR) + 색상 추출을
 * 한 번의 Vision API 호출로 함께 요청한다 (호출 비용/지연 절감).
 */
export async function annotateImage(imageBase64: string, apiKey: string): Promise<VisionAnnotations> {
  const response = await fetch(`${VISION_ENDPOINT}?key=${apiKey}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      requests: [
        {
          image: { content: imageBase64 },
          features: [
            { type: "LABEL_DETECTION", maxResults: 10 },
            { type: "TEXT_DETECTION" },
            { type: "IMAGE_PROPERTIES" },
          ],
        },
      ],
    }),
  });

  if (!response.ok) {
    throw new Error(`Vision API 오류 (${response.status}): ${await response.text()}`);
  }

  const data = await response.json();
  const result = data.responses?.[0] ?? {};

  const labels: string[] = (result.labelAnnotations ?? [])
    .map((label: { description?: string }) => (label.description ?? "").toLowerCase())
    .filter((label: string) => label.length > 0);

  const ocrText: string = result.fullTextAnnotation?.text ?? "";
  const dominantColor = result.imagePropertiesAnnotation?.dominantColors?.colors?.[0]?.color;

  return { labels, ocrText, dominantColor };
}
