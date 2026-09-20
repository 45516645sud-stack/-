// 기본 구조 확인용 샘플 데이터 (추후 실제 API 데이터로 교체 가능)
const FAIRS = [
  { title: '서울 국제 뷰티산업 박람회', region: '서울', date: '2026.03.05 ~ 2026.03.08' },
  { title: '대한민국 유아교육 박람회', region: '부산', date: '2026.03.12 ~ 2026.03.15' },
  { title: '스마트팩토리 산업기술 박람회', region: '경기', date: '2026.03.20 ~ 2026.03.23' },
  { title: '푸드위크 식품 박람회', region: '서울', date: '2026.04.01 ~ 2026.04.04' },
  { title: '웨딩 & 라이프스타일 박람회', region: '부산', date: '2026.04.10 ~ 2026.04.12' },
  { title: '창업&프랜차이즈 취업박람회', region: '대구', date: '2026.04.15 ~ 2026.04.17' },
];

const searchInput = document.getElementById('search-input');
const fairListEl = document.getElementById('fair-list');
const resultCountEl = document.getElementById('result-count');
const emptyMessageEl = document.getElementById('empty-message');

function renderFairs(fairs) {
  fairListEl.innerHTML = '';

  fairs.forEach((fair) => {
    const li = document.createElement('li');
    li.className = 'fair-item';
    li.innerHTML = `
      <h2>${fair.title}</h2>
      <p>📍 ${fair.region}</p>
      <p>🗓 ${fair.date}</p>
    `;
    fairListEl.appendChild(li);
  });

  resultCountEl.textContent = `총 ${fairs.length}건`;
  emptyMessageEl.hidden = fairs.length > 0;
}

function filterFairs(keyword) {
  const trimmed = keyword.trim();
  if (!trimmed) return FAIRS;
  return FAIRS.filter(
    (fair) => fair.title.includes(trimmed) || fair.region.includes(trimmed),
  );
}

searchInput.addEventListener('input', (e) => {
  renderFairs(filterFairs(e.target.value));
});

renderFairs(FAIRS);
