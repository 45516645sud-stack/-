import { useEffect, useMemo, useState } from 'react';
import CategoryTabs from '../components/CategoryTabs.jsx';
import FilterPanel from '../components/FilterPanel.jsx';
import FairList from '../components/FairList.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import { fetchFairs, feeCategory } from '../api/tourApi.js';
import { SAMPLE_FAIRS } from '../data/sampleFairs.js';
import { categorizeFair } from '../data/categories.js';

export default function HomePage() {
  const [keyword, setKeyword] = useState('박람회');
  const [submittedKeyword, setSubmittedKeyword] = useState('박람회');
  const [areaCode, setAreaCode] = useState('');
  const [fee, setFee] = useState('');
  const [category, setCategory] = useState('all');

  const [fairs, setFairs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorInfo, setErrorInfo] = useState(null); // { noApiKey, message } | null

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErrorInfo(null);
      try {
        const results = await fetchFairs({ keyword: submittedKeyword || '박람회', areaCode });
        if (!cancelled) setFairs(results);
      } catch (err) {
        if (cancelled) return;
        const noApiKey = err.message === 'NO_API_KEY';
        setErrorInfo({ noApiKey, message: noApiKey ? '' : err.message });
        const fallback = SAMPLE_FAIRS.map((f) => ({ ...f, category: categorizeFair(f.title) })).filter(
          (f) => !areaCode || f.areaCode === areaCode,
        );
        setFairs(fallback);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [submittedKeyword, areaCode]);

  const visibleFairs = useMemo(() => {
    return fairs.filter((fair) => {
      if (category !== 'all' && fair.category !== category) return false;
      if (fee && feeCategory(fair.fee) !== fee) return false;
      return true;
    });
  }, [fairs, category, fee]);

  return (
    <div className="home-page">
      <section className="hero">
        <h1>전국 박람회를 한눈에</h1>
        <p>카테고리, 지역, 무료/유료 조건으로 나에게 맞는 박람회를 찾아보세요.</p>
      </section>

      <FilterPanel
        keyword={keyword}
        onKeywordChange={setKeyword}
        areaCode={areaCode}
        onAreaChange={setAreaCode}
        fee={fee}
        onFeeChange={setFee}
        onSubmit={() => setSubmittedKeyword(keyword.trim())}
      />

      <CategoryTabs active={category} onChange={setCategory} />

      {errorInfo && <ErrorBanner noApiKey={errorInfo.noApiKey} message={errorInfo.message} />}

      {loading ? <LoadingSpinner /> : <FairList fairs={visibleFairs} />}
    </div>
  );
}
