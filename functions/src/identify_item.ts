import Busboy from "busboy";
import type { Request } from "firebase-functions/v2/https";
import { onRequest } from "firebase-functions/v2/https";
import { buildBatteryResult } from "./battery_info";
import { classifyImage } from "./classify_image";
import { extractPillFeatures, lookupPill, mfdsApiKey } from "./pill_lookup";
import { IdentifyResult } from "./types";

const MAX_IMAGE_BYTES = 8 * 1024 * 1024; // 인증 없는 공개 엔드포인트이므로 업로드 크기를 제한해 남용을 줄인다.

function readMultipartImage(req: Request): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const busboy = Busboy({
      headers: req.headers as Record<string, string>,
      limits: { fileSize: MAX_IMAGE_BYTES },
    });
    const chunks: Buffer[] = [];
    let found = false;
    let tooLarge = false;

    busboy.on("file", (_name: string, file: NodeJS.ReadableStream) => {
      found = true;
      file.on("data", (chunk: Buffer) => chunks.push(chunk));
      file.on("limit", () => {
        tooLarge = true;
        reject(new Error(`이미지 파일이 너무 큽니다. (최대 ${MAX_IMAGE_BYTES / 1024 / 1024}MB)`));
      });
    });
    busboy.on("finish", () => {
      if (tooLarge) return;
      if (!found) {
        reject(new Error("이미지 파일이 요청에 없습니다."));
        return;
      }
      resolve(Buffer.concat(chunks));
    });
    busboy.on("error", reject);
    busboy.end(req.rawBody);
  });
}

// Flutter 클라이언트의 HttpItemRecognitionRepository가 호출하는 엔드포인트.
// multipart/form-data로 받은 이미지를 분류한 뒤, 종류에 맞는 결과를 반환한다.
export const identifyItem = onRequest(
  { secrets: [mfdsApiKey], cors: true },
  async (req, res) => {
    if (req.method !== "POST") {
      res.status(405).json({ error: "POST 요청만 지원합니다." });
      return;
    }

    try {
      const imageBuffer = await readMultipartImage(req);
      const category = await classifyImage(imageBuffer);

      let result: IdentifyResult;
      switch (category) {
        case "battery":
          result = buildBatteryResult();
          break;
        case "pill": {
          const features = await extractPillFeatures(imageBuffer);
          result = await lookupPill(features);
          break;
        }
        default:
          // 약/건전지 어느 쪽으로도 판별되지 않은 경우: 잘못된 검색을 시도하는 대신
          // 재촬영을 안내한다.
          result = {
            matched: false,
            category: "unknown",
            name: "",
            description: "",
            disposalSteps: [],
            precautions: [],
          };
      }

      res.status(200).json(result);
    } catch (error) {
      console.error("identifyItem failed", error);
      res.status(500).json({ matched: false, error: "인식 처리 중 오류가 발생했습니다." });
    }
  }
);
