export const CATEGORIES = [
  { key: 'all', label: '전체', keywords: [] },
  { key: 'it', label: 'IT·테크', keywords: ['IT', '테크', '전자', '로봇', 'AI', '디지털', '소프트웨어'] },
  { key: 'beauty', label: '뷰티·미용', keywords: ['뷰티', '미용', '화장품', '헤어'] },
  { key: 'baby', label: '유아·교육', keywords: ['유아', '베이비', '키즈', '교육', '완구'] },
  { key: 'food', label: '푸드·식품', keywords: ['푸드', '식품', '음식', '커피', '와인', '주류'] },
  { key: 'job', label: '취업·창업', keywords: ['취업', '창업', '채용', '프랜차이즈'] },
  { key: 'life', label: '웨딩·라이프', keywords: ['웨딩', '결혼', '라이프', '인테리어', '홈', '리빙'] },
  { key: 'culture', label: '문화·예술', keywords: ['문화', '예술', '아트', '디자인', '공예'] },
  // 아래 두 카테고리는 키워드가 일반적이라(다른 분야 이름과 겹칠 수 있음) 가장 나중에 매칭합니다.
  { key: 'industry', label: '산업·무역', keywords: ['산업', '무역', '기계', '자동차', '부품', '공작', '반도체'] },
  { key: 'etc', label: '기타', keywords: [] },
];

export function categorizeFair(title = '') {
  for (const category of CATEGORIES) {
    if (category.key === 'all' || category.key === 'etc') continue;
    if (category.keywords.some((kw) => title.includes(kw))) {
      return category.key;
    }
  }
  return 'etc';
}
