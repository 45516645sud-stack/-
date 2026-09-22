/**
 * 자연어 문장을 서버(/api/ai-search, Vite 개발 서버 미들웨어)로 보내
 * 가장 알맞은 카테고리와 검색 키워드를 돌려받습니다.
 * ANTHROPIC_API_KEY는 서버(.env, VITE_ 접두사 없음)에만 있고 브라우저로 내려오지 않습니다.
 */
export async function askAiForCategory(query) {
  const res = await fetch('/api/ai-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    if (data.error === 'NO_API_KEY' || data.error === 'INVALID_API_KEY') {
      throw new Error('NO_API_KEY');
    }
    if (data.error === 'RATE_LIMITED') {
      throw new Error('AI 요청이 많아서 잠시 후 다시 시도해야 해요.');
    }
    throw new Error(data.message || 'AI 추천을 가져오지 못했어요.');
  }

  return data; // { category, keyword, reason }
}
