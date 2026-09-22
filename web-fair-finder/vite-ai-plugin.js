import Anthropic from '@anthropic-ai/sdk';
import { CATEGORIES } from './src/data/categories.js';

// 카테고리 목록을 프롬프트에 넣을 텍스트로 만들어둠 (etc 제외, all 제외)
const CATEGORY_PROMPT_LIST = CATEGORIES.filter((c) => c.key !== 'all' && c.key !== 'etc')
  .map((c) => `- ${c.key}: ${c.label}`)
  .join('\n');

const VALID_CATEGORY_KEYS = new Set(CATEGORIES.map((c) => c.key));

const SYSTEM_PROMPT = `당신은 박람회 찾기 앱의 카테고리 분류기입니다.
사용자가 자연어로 입력한 요청을 보고, 아래 카테고리 중 가장 알맞은 것 하나와
박람회 검색에 쓸 키워드(한국어, 1~4단어)를 고르세요.

카테고리 목록:
${CATEGORY_PROMPT_LIST}
- etc: 기타 (위에 맞는 게 전혀 없을 때만)

반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트나 설명은 포함하지 마세요.
{"category": "카테고리 key", "keyword": "검색 키워드", "reason": "이 카테고리를 고른 이유를 사용자에게 보여줄 한 문장"}`;

function readRequestBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
    });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

function extractJson(text) {
  const trimmed = text.trim();
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/);
  const raw = fenced ? fenced[1].trim() : trimmed;
  return JSON.parse(raw);
}

/**
 * ANTHROPIC_API_KEY(서버 전용, VITE_ 접두사 없음)를 이용해
 * 브라우저에 키를 노출하지 않고 /api/ai-search 에서 Claude를 호출하는 Vite 개발 서버 플러그인.
 * `vite dev` 에서만 동작합니다 (vite build/preview에는 포함되지 않음).
 */
export function aiSearchPlugin() {
  return {
    name: 'ai-search-middleware',
    configureServer(server) {
      server.middlewares.use('/api/ai-search', async (req, res) => {
        if (req.method !== 'POST') {
          res.statusCode = 405;
          res.end(JSON.stringify({ error: 'METHOD_NOT_ALLOWED' }));
          return;
        }

        const apiKey = process.env.ANTHROPIC_API_KEY;
        if (!apiKey) {
          res.statusCode = 401;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ error: 'NO_API_KEY' }));
          return;
        }

        try {
          const body = JSON.parse(await readRequestBody(req));
          const query = (body.query || '').toString().slice(0, 500);
          if (!query.trim()) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'EMPTY_QUERY' }));
            return;
          }

          const client = new Anthropic({ apiKey });
          const response = await client.messages.create({
            model: 'claude-opus-5',
            max_tokens: 300,
            output_config: { effort: 'low' },
            system: SYSTEM_PROMPT,
            messages: [{ role: 'user', content: query }],
          });

          const textBlock = response.content.find((b) => b.type === 'text');
          if (!textBlock) throw new Error('NO_TEXT_RESPONSE');

          const parsed = extractJson(textBlock.text);
          const category = VALID_CATEGORY_KEYS.has(parsed.category) ? parsed.category : 'etc';

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(
            JSON.stringify({
              category,
              keyword: (parsed.keyword || '박람회').toString(),
              reason: (parsed.reason || '').toString(),
            }),
          );
        } catch (err) {
          const isAuthError = err?.status === 401 || err?.status === 403;
          const isRateLimit = err?.status === 429;
          res.statusCode = isAuthError ? 401 : isRateLimit ? 429 : 500;
          res.setHeader('Content-Type', 'application/json');
          res.end(
            JSON.stringify({
              error: isAuthError ? 'INVALID_API_KEY' : isRateLimit ? 'RATE_LIMITED' : 'AI_ERROR',
              message: err?.message ?? String(err),
            }),
          );
        }
      });
    },
  };
}
