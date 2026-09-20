import { REGIONS } from '../data/regions.js';

const FEE_OPTIONS = [
  { key: '', label: '전체' },
  { key: 'free', label: '무료' },
  { key: 'paid', label: '유료' },
];

export default function FilterPanel({ keyword, onKeywordChange, areaCode, onAreaChange, fee, onFeeChange, onSubmit }) {
  return (
    <form
      className="filter-panel"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <input
        type="search"
        className="filter-input"
        placeholder="박람회 이름 검색 (예: 뷰티, 산업, 유아)"
        value={keyword}
        onChange={(e) => onKeywordChange(e.target.value)}
        aria-label="박람회 검색어"
      />

      <select className="filter-select" value={areaCode} onChange={(e) => onAreaChange(e.target.value)} aria-label="지역">
        {REGIONS.map((r) => (
          <option key={r.code} value={r.code}>
            {r.name}
          </option>
        ))}
      </select>

      <select className="filter-select" value={fee} onChange={(e) => onFeeChange(e.target.value)} aria-label="요금">
        {FEE_OPTIONS.map((f) => (
          <option key={f.key} value={f.key}>
            {f.label}
          </option>
        ))}
      </select>

      <button type="submit" className="filter-submit">
        검색
      </button>
    </form>
  );
}
