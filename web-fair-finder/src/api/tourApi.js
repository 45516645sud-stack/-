import { TOUR_API_BASE, TOUR_API_KEY, HAS_API_KEY, MOBILE_OS, MOBILE_APP } from './config.js';
import { categorizeFair } from '../data/categories.js';

const CONTENT_TYPE_FESTIVAL = 15; // 축제/공연/행사 (박람회 포함)

function buildQuery(params) {
  const query = new URLSearchParams({
    serviceKey: TOUR_API_KEY,
    MobileOS: MOBILE_OS,
    MobileApp: MOBILE_APP,
    _type: 'json',
    ...params,
  });
  return query.toString();
}

async function callTourApi(endpoint, params) {
  const url = `${TOUR_API_BASE}/${endpoint}?${buildQuery(params)}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`TourAPI 요청 실패 (${res.status})`);
  }
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error('TourAPI 응답을 해석할 수 없습니다 (서비스키를 확인하세요).');
  }
  const resultCode = json?.response?.header?.resultCode;
  if (resultCode && resultCode !== '0000') {
    throw new Error(json.response.header.resultMsg || 'TourAPI 오류 응답');
  }
  const items = json?.response?.body?.items?.item;
  if (!items) return [];
  return Array.isArray(items) ? items : [items];
}

function normalizeListItem(item) {
  const title = item.title ?? '';
  return {
    contentId: String(item.contentid),
    title,
    category: categorizeFair(title),
    areaCode: String(item.areacode ?? ''),
    addr: [item.addr1, item.addr2].filter(Boolean).join(' '),
    image: item.firstimage || item.firstimage2 || '',
    tel: item.tel || '',
    mapx: item.mapx,
    mapy: item.mapy,
  };
}

export function feeCategory(feeText) {
  if (!feeText) return 'unknown';
  // "유료"가 명시된 경우 "일부 무료" 같은 조건부 문구가 섞여 있어도 유료로 분류합니다.
  if (feeText.includes('유료') || /\d/.test(feeText) || feeText.includes('원')) return 'paid';
  if (feeText.includes('무료')) return 'free';
  return 'unknown';
}

function normalizeIntro(item) {
  if (!item) return {};
  return {
    startDate: item.eventstartdate || '',
    endDate: item.eventenddate || '',
    fee: item.usetimefestival || item.discountinfofestival || '',
    place: item.eventplace || '',
    homepage: item.eventhomepage ? stripHtml(item.eventhomepage) : '',
    sponsor: item.sponsor1 || '',
    sponsorTel: item.sponsor1tel || '',
    playtime: item.playtime || '',
  };
}

function stripHtml(html) {
  return html.replace(/<[^>]*>/g, '').trim();
}

/**
 * 키워드(기본값 "박람회") + 지역코드로 목록을 가져오고,
 * 각 항목의 상세 소개(detailIntro2)를 병렬로 조회해 일정/요금 정보를 덧붙입니다.
 */
export async function fetchFairs({ keyword = '박람회', areaCode = '', pageNo = 1, numOfRows = 12 } = {}) {
  if (!HAS_API_KEY) {
    throw new Error('NO_API_KEY');
  }

  const listParams = {
    keyword,
    contentTypeId: CONTENT_TYPE_FESTIVAL,
    numOfRows,
    pageNo,
    arrange: 'A',
  };
  if (areaCode) listParams.areaCode = areaCode;

  const rawItems = await callTourApi('searchKeyword2', listParams);
  const list = rawItems.map(normalizeListItem);

  const enriched = await Promise.all(
    list.map(async (fair) => {
      try {
        const introItems = await callTourApi('detailIntro2', {
          contentId: fair.contentId,
          contentTypeId: CONTENT_TYPE_FESTIVAL,
        });
        return { ...fair, ...normalizeIntro(introItems[0]) };
      } catch {
        return fair;
      }
    }),
  );

  return enriched;
}

export async function fetchFairDetail(contentId) {
  if (!HAS_API_KEY) {
    throw new Error('NO_API_KEY');
  }

  const [commonItems, introItems] = await Promise.all([
    callTourApi('detailCommon2', {
      contentId,
      defaultYN: 'Y',
      firstImageYN: 'Y',
      areacodeYN: 'Y',
      addrinfoYN: 'Y',
      overviewYN: 'Y',
      tel: '',
    }),
    callTourApi('detailIntro2', {
      contentId,
      contentTypeId: CONTENT_TYPE_FESTIVAL,
    }),
  ]);

  const common = commonItems[0] ?? {};
  const intro = normalizeIntro(introItems[0]);

  return {
    contentId,
    title: common.title ?? '',
    category: categorizeFair(common.title ?? ''),
    areaCode: String(common.areacode ?? ''),
    addr: [common.addr1, common.addr2].filter(Boolean).join(' '),
    image: common.firstimage || common.firstimage2 || '',
    tel: common.tel || intro.sponsorTel || '',
    overview: common.overview ? stripHtml(common.overview) : '',
    homepage: common.homepage ? stripHtml(common.homepage) : intro.homepage,
    ...intro,
  };
}
