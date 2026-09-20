// 공공데이터포털(data.go.kr)의 "한국관광공사_국문 관광정보 서비스_GW"(TourAPI)에서
// 발급받은 서비스키를 .env 파일의 VITE_TOUR_API_KEY 에 설정하세요.
// 키가 없으면 앱은 자동으로 샘플 데이터로 동작합니다.
export const TOUR_API_KEY = import.meta.env.VITE_TOUR_API_KEY ?? '';
export const HAS_API_KEY = TOUR_API_KEY.trim().length > 0;

// 개발 서버에서는 vite.config.js 의 프록시(/tourapi)를 사용해 CORS 문제를 피합니다.
export const TOUR_API_BASE = '/tourapi';

export const MOBILE_OS = 'ETC';
export const MOBILE_APP = 'FairFinder';
