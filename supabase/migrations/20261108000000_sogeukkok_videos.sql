-- 소극콕: 스토리에 넣을 공연 홍보 영상(유튜브). 누구나 읽고, 관리자(sk_admins 에 있는 계정)만 고친다.
create table if not exists public.sk_admins (
  user_id uuid primary key references auth.users (id) on delete cascade
);
alter table public.sk_admins enable row level security;
revoke all on public.sk_admins from anon, authenticated;

create table if not exists public.sk_videos (
  fair_id text primary key check (char_length(fair_id) between 1 and 80),
  vid text check (vid is null or vid ~ '^[A-Za-z0-9_-]{11}$'),
  status text not null check (status in ('ok', 'no')),
  updated_at timestamptz not null default now()
);
alter table public.sk_videos enable row level security;

create or replace function public.sk_is_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.sk_admins where user_id = auth.uid())
$$;
revoke all on function public.sk_is_admin() from public;
grant execute on function public.sk_is_admin() to anon, authenticated;

drop policy if exists "sk_videos 누구나 읽기" on public.sk_videos;
create policy "sk_videos 누구나 읽기" on public.sk_videos for select to anon, authenticated using (true);
drop policy if exists "sk_videos 관리자 쓰기" on public.sk_videos;
create policy "sk_videos 관리자 쓰기" on public.sk_videos for all to authenticated using (public.sk_is_admin()) with check (public.sk_is_admin());

grant select on public.sk_videos to anon, authenticated;
grant insert, update, delete on public.sk_videos to authenticated;
