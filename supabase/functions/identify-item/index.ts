import { encodeBase64 } from "jsr:@std/encoding@1/base64";
import { corsHeaders } from "../_shared/cors.ts";
import { AuthError, verifySupabaseSession } from "./auth.ts";
import { buildBatteryResult } from "./battery_info.ts";
import { classifyCategory } from "./classify_image.ts";
import { extractPillFeatures, lookupPill } from "./pill_lookup.ts";
import { IdentifyResult } from "./types.ts";
import { annotateImage } from "./vision.ts";

const MAX_IMAGE_BYTES = 8 * 1024 * 1024; // 업로드 크기 제한으로 남용을 줄인다.

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// Flutter 클라이언트의 HttpItemRecognitionRepository가 호출하는 엔드포인트.
// multipart/form-data로 받은 이미지를 분류한 뒤, 종류에 맞는 결과를 반환한다.
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return jsonResponse({ error: "POST 요청만 지원합니다." }, 405);
  }

  try {
    await verifySupabaseSession(req);
  } catch (error) {
    const message = error instanceof AuthError ? error.message : "인증 확인에 실패했습니다.";
    console.warn("identify-item auth check failed:", message);
    return jsonResponse({ matched: false, error: message }, 401);
  }

  try {
    const formData = await req.formData();
    const imageFile = formData.get("image");
    if (!(imageFile instanceof File)) {
      return jsonResponse({ matched: false, error: "이미지 파일이 요청에 없습니다." }, 400);
    }
    if (imageFile.size > MAX_IMAGE_BYTES) {
      return jsonResponse(
        { matched: false, error: `이미지 파일이 너무 큽니다. (최대 ${MAX_IMAGE_BYTES / 1024 / 1024}MB)` },
        413,
      );
    }

    const imageBuffer = new Uint8Array(await imageFile.arrayBuffer());
    const imageBase64 = encodeBase64(imageBuffer);

    const visionApiKey = Deno.env.get("GOOGLE_VISION_API_KEY");
    if (!visionApiKey) {
      throw new Error("GOOGLE_VISION_API_KEY 시크릿이 설정되지 않았습니다.");
    }

    const annotations = await annotateImage(imageBase64, visionApiKey);
    const category = classifyCategory(annotations.labels);

    let result: IdentifyResult;
    switch (category) {
      case "battery":
        result = buildBatteryResult();
        break;
      case "pill": {
        const mfdsApiKey = Deno.env.get("MFDS_API_KEY");
        if (!mfdsApiKey) {
          throw new Error("MFDS_API_KEY 시크릿이 설정되지 않았습니다.");
        }
        const features = extractPillFeatures(annotations);
        result = await lookupPill(features, mfdsApiKey);
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

    return jsonResponse(result, 200);
  } catch (error) {
    console.error("identify-item failed:", error);
    return jsonResponse({ matched: false, error: "인식 처리 중 오류가 발생했습니다." }, 500);
  }
});
