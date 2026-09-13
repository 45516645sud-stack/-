import type { Request } from "firebase-functions/v2/https";
import { admin } from "./firebase_admin";

export class AppCheckError extends Error {}

const APP_CHECK_HEADER = "X-Firebase-AppCheck";

/**
 * onRequest 함수는 onCall과 달리 App Check를 자동으로 강제하지 않으므로
 * 직접 헤더를 검증한다. 유료 API(Vision, 식약처)를 호출하기 전에
 * 정식 앱에서 온 요청인지 확인하는 용도.
 * https://firebase.google.com/docs/app-check/cloud-functions#https-functions
 */
export async function verifyAppCheck(req: Request): Promise<void> {
  const token = req.header(APP_CHECK_HEADER);
  if (!token) {
    throw new AppCheckError("App Check 토큰이 없습니다.");
  }

  try {
    await admin.appCheck().verifyToken(token);
  } catch (error) {
    throw new AppCheckError("유효하지 않은 App Check 토큰입니다.");
  }
}
