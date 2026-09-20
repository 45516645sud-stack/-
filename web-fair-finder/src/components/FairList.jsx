import FairCard from './FairCard.jsx';

export default function FairList({ fairs }) {
  if (fairs.length === 0) {
    return <p className="empty-state">조건에 맞는 박람회를 찾지 못했어요. 검색어나 필터를 바꿔보세요.</p>;
  }

  return (
    <div className="fair-grid">
      {fairs.map((fair) => (
        <FairCard key={fair.contentId} fair={fair} />
      ))}
    </div>
  );
}
