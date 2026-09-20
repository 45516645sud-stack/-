import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchFairDetail } from '../api/tourApi.js';
import { SAMPLE_FAIRS } from '../data/sampleFairs.js';
import { categorizeFair, CATEGORIES } from '../data/categories.js';
import { formatDateRange } from '../utils/format.js';
import { regionName } from '../data/regions.js';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';

export default function FairDetailPage() {
  const { contentId } = useParams();
  const [fair, setFair] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorInfo, setErrorInfo] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErrorInfo(null);
      try {
        const detail = await fetchFairDetail(contentId);
        if (!cancelled) setFair(detail);
      } catch (err) {
        if (cancelled) return;
        const noApiKey = err.message === 'NO_API_KEY';
        setErrorInfo({ noApiKey, message: noApiKey ? '' : err.message });
        const sample = SAMPLE_FAIRS.find((f) => f.contentId === contentId) ?? SAMPLE_FAIRS[0];
        setFair({ ...sample, category: categorizeFair(sample.title) });
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [contentId]);

  if (loading) return <LoadingSpinner />;
  if (!fair) return <p className="empty-state">박람회 정보를 찾을 수 없습니다.</p>;

  const categoryLabel = CATEGORIES.find((c) => c.key === fair.category)?.label ?? '기타';

  return (
    <div className="fair-detail">
      <Link to="/" className="back-link">
        ← 목록으로
      </Link>

      {errorInfo && <ErrorBanner noApiKey={errorInfo.noApiKey} message={errorInfo.message} />}

      <div className="fair-detail-image">
        {fair.image ? <img src={fair.image} alt={fair.title} /> : <div className="fair-card-image-placeholder large">🎪</div>}
      </div>

      <span className="badge badge-category">{categoryLabel}</span>
      <h1>{fair.title}</h1>

      <dl className="fair-detail-info">
        <div>
          <dt>기간</dt>
          <dd>{formatDateRange(fair.startDate, fair.endDate)}</dd>
        </div>
        <div>
          <dt>장소</dt>
          <dd>{fair.place || fair.addr || regionName(fair.areaCode)}</dd>
        </div>
        <div>
          <dt>요금</dt>
          <dd>{fair.fee || '정보 없음'}</dd>
        </div>
        {fair.tel && (
          <div>
            <dt>문의</dt>
            <dd>{fair.tel}</dd>
          </div>
        )}
        {fair.homepage && (
          <div>
            <dt>홈페이지</dt>
            <dd>
              <a href={fair.homepage} target="_blank" rel="noreferrer">
                {fair.homepage}
              </a>
            </dd>
          </div>
        )}
      </dl>

      {fair.overview && (
        <section className="fair-detail-overview">
          <h2>소개</h2>
          <p>{fair.overview}</p>
        </section>
      )}
    </div>
  );
}
