-- 폐의약품/폐건전지 수거함 위치 테이블.
create table if not exists public.collection_boxes (
  id text primary key,
  name text not null,
  address text not null,
  latitude double precision not null,
  longitude double precision not null,
  -- 이 수거함이 받는 품목 종류: 'pill' | 'battery' (둘 다 받으면 두 값 모두 포함)
  categories text[] not null default '{}'
);

-- 앱에 로그인 기능이 없어 익명 사용자도 수거함 위치를 조회할 수 있어야 한다.
alter table public.collection_boxes enable row level security;

create policy "collection_boxes are publicly readable"
  on public.collection_boxes
  for select
  to anon, authenticated
  using (true);

-- insert/update/delete에 대한 정책을 두지 않는다 = RLS가 기본적으로 모두 거부.
-- 시드 업로드는 RLS를 우회하는 service_role 키로만 수행한다
-- (supabase/seed/seed_collection_boxes.ts 참고).
