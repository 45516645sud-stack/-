import { createClient } from "jsr:@supabase/supabase-js@2";

export class AuthError extends Error {}

/**
 * 이 함수는 유료 API(Vision, 식약처)를 호출하므로 아무나 URL만으로
 * 무제한 호출하지 못하게 막아야 한다. 원래(Firebase) 버전은 App Check로
 * "정식 앱에서 온 요청인지" 기기 증명까지 확인했지만, Supabase에는
 * 직접적인 대응 제품이 없다.
 *
 * 대신 여기서는 Authorization 헤더의 토큰이 실제 Supabase 세션(로그인
 * 화면이 없는 앱이라 대부분 익명 로그인 세션)인지 직접 검증한다.
 * 플랫폼 기본 제공 verify_jwt는 새 publishable/secret 키 체계와 호환되지
 * 않아(JWT 형식이 아님) supabase/config.toml에서 꺼두고 이 검사로 대체했다.
 * App Check의 "기기 증명" 수준은 아니지만, 최소한 유효한 Supabase 클라이언트
 * 세션 없이는 호출할 수 없게 만든다.
 */
export async function verifySupabaseSession(req: Request): Promise<void> {
  const authHeader = req.headers.get("Authorization");
  const token = authHeader?.replace(/^Bearer\s+/i, "").trim();
  if (!token) {
    throw new AuthError("인증 토큰이 없습니다.");
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  // 신/구 키 체계 모두 대응: SUPABASE_ANON_KEY(구)가 없으면 새 publishable 키를 쓴다.
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? Deno.env.get("SUPABASE_PUBLISHABLE_KEYS");
  if (!supabaseUrl || !anonKey) {
    throw new Error("SUPABASE_URL/키 환경변수가 없습니다.");
  }

  const client = createClient(supabaseUrl, anonKey);
  const { data, error } = await client.auth.getUser(token);
  if (error || !data.user) {
    throw new AuthError("유효하지 않은 인증 토큰입니다.");
  }
}
