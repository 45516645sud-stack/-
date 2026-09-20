import { CATEGORIES } from '../data/categories.js';

export default function CategoryTabs({ active, onChange }) {
  return (
    <div className="category-tabs" role="tablist" aria-label="카테고리">
      {CATEGORIES.map((cat) => (
        <button
          key={cat.key}
          role="tab"
          aria-selected={active === cat.key}
          className={`category-tab${active === cat.key ? ' active' : ''}`}
          onClick={() => onChange(cat.key)}
        >
          {cat.label}
        </button>
      ))}
    </div>
  );
}
