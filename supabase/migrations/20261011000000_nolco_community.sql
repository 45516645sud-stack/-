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
