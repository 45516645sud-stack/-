import { useState } from 'react';
import { askAiForCategory } from '../api/aiSearch.js';
import { CATEGORIES } from '../data/categories.js';

export default function AiSearchBox({ onResult }) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastReason, setLastReason] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);
    setLastReason('');

    try {
      const result = await askAiForCategory(trimmed);
      const label = CATEGORIES.find((c) => c.key === result.category)?.label ?? '기타';
      setLastReason(`✨ "${label}" 카테고리로 찾아봤어요${result.reason ? ` — ${result.reason}` : ''}`);
      onResult(result);
    } catch (err) {
      if (err.message === 'NO_API_KEY') {
        setError(
          'AI 검색을 쓰려면 서버에 Anthropic API 키가 필요해요. web-fair-finder/.env 파일에 ANTHROPIC_API_KEY를 설정하고 dev 서버를 다시 시작하세요.',
        );
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ai-search">
      <form className="ai-search-form" onSubmit={handleSubmit}>
        <span className="ai-search-icon" aria-hidden="true">✨</span>
        <input
          type="text"
          className="ai-search-input"
          placeholder="예: 아이랑 같이 갈만한 곳 있을까요? / 취업 준비 중이라 도움될 박람회 찾아줘"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="AI에게 박람회 물어보기"
        />
        <button type="submit" className="ai-search-submit" disabled={loading || !query.trim()}>
          {loading ? '찾는 중...' : 'AI로 찾기'}
        </button>
      </form>
      {error && <p className="ai-search-message ai-search-error">{error}</p>}
      {!error && lastReason && <p className="ai-search-message ai-search-reason">{lastReason}</p>}
    </div>
  );
}
