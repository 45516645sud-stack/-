import { Link } from 'react-router-dom';
import { formatDateRange } from '../utils/format.js';
import { regionName } from '../data/regions.js';

export default function FairCard({ fair }) {
  return (
    <Link to={`/fair/${fair.contentId}`} className="fair-card">
      <div className="fair-card-image">
        {fair.image ? (
          <img src={fair.image} alt={fair.title} loading="lazy" />
        ) : (
          <div className="fair-card-image-placeholder">🎪</div>
        )}
        {fair.isSample && <span className="badge badge-sample">샘플</span>}
      </div>
      <div className="fair-card-body">
        <h3 className="fair-card-title">{fair.title}</h3>
        <p className="fair-card-meta">{formatDateRange(fair.startDate, fair.endDate)}</p>
        <p className="fair-card-meta">📍 {regionName(fair.areaCode)}</p>
        {fair.fee && <p className="fair-card-fee">{fair.fee}</p>}
      </div>
    </Link>
  );
}
