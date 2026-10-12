-- 놀코: 리뷰·직접 만든 코스 저장 (서버 함수만 읽고 쓴다. RLS를 켜고 정책을 두지 않아 브라우저에서 바로는 못 건드림)
create table if not exists public.nolco_docs (
  col text not null check (col in ('rv', 'uc')),
  id text not null,
  body jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  primary key (col, id)
);
alter table public.nolco_docs enable row level security;

-- 신고: 같은 사람이 같은 항목을 여러 번 신고해도 한 번
create table if not exists public.nolco_reports (
  col text not null,
  doc_id text not null,
  item_id text not null,
  reporter text not null,
  created_at timestamptz not null default now(),
  primary key (col, doc_id, item_id, reporter)
);
alter table public.nolco_reports enable row level security;

-- 쓰기 횟수 제한용 (IP 해시, 시각). 하루 지난 기록은 함수가 지운다
create table if not exists public.nolco_hits (
  ip text not null,
  at timestamptz not null default now()
);
create index if not exists nolco_hits_ip_at on public.nolco_hits (ip, at);
alter table public.nolco_hits enable row level security;

-- 방문 통계: 날짜·종류·대상별 횟수만 (누가 봤는지는 남기지 않음)
create table if not exists public.nolco_stats (
  day date not null default current_date,
  ev text not null,
  item text not null default '',
  n integer not null default 0,
  primary key (day, ev, item)
);
alter table public.nolco_stats enable row level security;

-- 팝업스토어 승인: 관리자가 맞다고 한 것(ok=true)만 앱에 나온다. item 은 승인할 때의 이름·장소·기간
create table if not exists public.nolco_popups (
  id text primary key,
  ok boolean not null,
  item jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.nolco_popups enable row level security;
