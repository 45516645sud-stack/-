import * as Busboy from "busboy";
import { onRequest } from "firebase-functions/v2/https";
import { buildBatteryResult } from "./battery_info";
import { classifyImage } from "./classify_image";
import { extractPillFeatures, lookupPill, mfdsApiKey } from "./pill_lookup";
import { IdentifyResult } from "./types";

function readMultipartImage(req: import("express").Request): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const busboy = Busboy({ headers: req.headers });
    const chunks: Buffer[] = [];
    let found = false;

    busboy.on("file", (_name, file) => {
      found = true;
      file.on("data", (chunk: Buffer) => chunks.push(chunk));
    });
    busboy.on("finish", () => {
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
      if (category === "battery") {
        result = buildBatteryResult();
      } else {
        const features = await extractPillFeatures(imageBuffer);
        result = await lookupPill(features);
      }

      res.status(200).json(result);
    } catch (error) {
      console.error("identifyItem failed", error);
      res.status(500).json({ matched: false, error: "인식 처리 중 오류가 발생했습니다." });
    }
  }
);
