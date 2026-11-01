-- 소극콕: 로그인한 사람의 찜(공연 id). 브라우저가 공개 키로 직접 읽고 쓰되, RLS 로 자기 것만 보이고 고칠 수 있다.
create table if not exists public.sk_favs (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  fair_id text not null check (char_length(fair_id) between 1 and 80),
  created_at timestamptz not null default now(),
  primary key (user_id, fair_id)
);
alter table public.sk_favs enable row level security;

drop policy if exists "sk_favs 내 것 보기" on public.sk_favs;
create policy "sk_favs 내 것 보기" on public.sk_favs for select to authenticated using (user_id = auth.uid());
drop policy if exists "sk_favs 내 것 넣기" on public.sk_favs;
create policy "sk_favs 내 것 넣기" on public.sk_favs for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "sk_favs 내 것 빼기" on public.sk_favs;
create policy "sk_favs 내 것 빼기" on public.sk_favs for delete to authenticated using (user_id = auth.uid());

revoke all on public.sk_favs from anon;
grant select, insert, delete on public.sk_favs to authenticated;

-- 한 사람이 찜을 너무 많이 쌓지 않게 (공연 수보다 넉넉히)
create or replace function public.sk_favs_limit() returns trigger language plpgsql as $$
begin
  if (select count(*) from public.sk_favs where user_id = new.user_id) >= 2000 then
    raise exception '찜은 2000개까지예요';
  end if;
  return new;
end $$;
drop trigger if exists sk_favs_limit on public.sk_favs;
create trigger sk_favs_limit before insert on public.sk_favs for each row execute function public.sk_favs_limit();

-- 회원 탈퇴: 로그인한 본인의 계정을 지운다 (찜은 on delete cascade 로 같이 지워짐)
create or replace function public.sk_delete_me() returns void
language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then raise exception '로그인이 필요해요'; end if;
  delete from auth.users where id = auth.uid();
end $$;
revoke all on function public.sk_delete_me() from public, anon;
grant execute on function public.sk_delete_me() to authenticated;
