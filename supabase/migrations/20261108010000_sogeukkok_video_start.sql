-- 소극콕: 홍보 영상에서 하이라이트가 시작하는 초 (이 시각부터 15초만 스토리에서 재생)
alter table public.sk_videos add column if not exists start_s integer check (start_s is null or start_s between 0 and 36000);
