-- =====================================================================
--  ナグ・ハマディ写本コーパス — コミュニティ機能（コメント・注釈・誤りの指摘）
--  Supabase (PostgreSQL) スキーマ。Supabase ダッシュボードの SQL Editor に
--  このファイル全体を貼り付けて 1 回実行してください（再実行しても安全です）。
--
--  方針
--   * 投稿はすべて status = 'pending'（承認待ち）で保存され、運営（admins）が
--     承認したものだけが一般公開されます。
--   * 投稿者は自分の投稿を状態にかかわらず閲覧でき、承認前なら削除できます。
--   * 運営かどうかは admins テーブルで管理します（下の「運営者の登録」参照）。
--   * メールアドレスは公開されません（公開されるのは表示名のみ）。
-- =====================================================================

-- ---------- 表示名（プロフィール） ----------
create table if not exists public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  display_name text not null check (char_length(display_name) between 1 and 60),
  created_at   timestamptz not null default now()
);

-- ---------- 運営者 ----------
create table if not exists public.admins (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  created_at timestamptz not null default now()
);

-- ---------- 投稿（コメント・注釈・誤りの指摘） ----------
do $$ begin
  create type public.contribution_kind as enum ('comment', 'annotation', 'correction');
exception when duplicate_object then null; end $$;
do $$ begin
  create type public.contribution_status as enum ('pending', 'approved', 'rejected');
exception when duplicate_object then null; end $$;

create table if not exists public.contributions (
  id             bigint generated always as identity primary key,
  doc            text not null check (doc ~ '^[a-z0-9_-]{1,40}$'),     -- 例: eugnostos, republic
  witness        text check (witness is null or witness ~ '^[A-Za-z0-9_-]{1,20}$'),  -- 例: III, V
  seg_id         text check (seg_id is null or char_length(seg_id) <= 80),         -- 本文 <s xml:id>（null = 文書全体）
  seg_label      text check (seg_label is null or char_length(seg_label) <= 40),   -- 表示用の § 番号
  token_index    int  check (token_index is null or token_index between 0 and 10000),
  token_form     text check (token_form is null or char_length(token_form) <= 120),
  kind           public.contribution_kind   not null default 'comment',
  body           text not null check (char_length(btrim(body)) between 1 and 4000),
  suggestion     text check (suggestion is null or char_length(suggestion) <= 1000),
  status         public.contribution_status not null default 'pending',
  author_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  author_name    text,
  moderator_note text check (moderator_note is null or char_length(moderator_note) <= 2000),
  created_at     timestamptz not null default now(),
  reviewed_at    timestamptz,
  reviewed_by    uuid references auth.users (id) on delete set null
);
create index if not exists contributions_doc_idx    on public.contributions (doc, status);
create index if not exists contributions_status_idx on public.contributions (status, created_at);

-- ---------- 運営判定 ----------
create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;
grant execute on function public.is_admin() to anon, authenticated;

-- ---------- 新規ユーザー → プロフィール自動作成 ----------
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, display_name)
  values (
    new.id,
    left(coalesce(
      nullif(btrim(new.raw_user_meta_data ->> 'display_name'), ''),
      nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''),
      nullif(btrim(new.raw_user_meta_data ->> 'name'), ''),
      'user-' || left(new.id::text, 6)            -- メールアドレスは表示名に使わない
    ), 60)
  )
  on conflict (id) do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- 投稿時の正規化（承認状態は投稿者が決められない） ----------
create or replace function public.contributions_before_insert()
returns trigger language plpgsql security definer set search_path = public as $$
declare n_pending int;
begin
  new.author_id   := auth.uid();
  new.status      := 'pending';
  new.reviewed_at := null;
  new.reviewed_by := null;
  new.moderator_note := null;
  new.created_at  := now();
  select display_name into new.author_name from public.profiles where id = auth.uid();
  -- 連投対策: 1 人あたりの承認待ちは 30 件まで
  select count(*) into n_pending from public.contributions
    where author_id = auth.uid() and status = 'pending';
  if n_pending >= 30 then
    raise exception 'too many pending contributions';
  end if;
  return new;
end $$;
drop trigger if exists contributions_bi on public.contributions;
create trigger contributions_bi before insert on public.contributions
  for each row execute function public.contributions_before_insert();

-- 承認・却下の記録（運営による更新時）
create or replace function public.contributions_before_update()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.status is distinct from old.status then
    new.reviewed_at := now();
    new.reviewed_by := auth.uid();
  end if;
  -- 本文・投稿者は運営でも書き換えない
  new.author_id := old.author_id; new.author_name := old.author_name;
  new.body := old.body; new.suggestion := old.suggestion; new.created_at := old.created_at;
  return new;
end $$;
drop trigger if exists contributions_bu on public.contributions;
create trigger contributions_bu before update on public.contributions
  for each row execute function public.contributions_before_update();

-- ---------- 行レベルセキュリティ ----------
alter table public.profiles      enable row level security;
alter table public.admins        enable row level security;
alter table public.contributions enable row level security;

drop policy if exists "profiles: read own or admin"  on public.profiles;
drop policy if exists "profiles: update own"         on public.profiles;
create policy "profiles: read own or admin" on public.profiles
  for select using (id = auth.uid() or public.is_admin());
create policy "profiles: update own" on public.profiles
  for update using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists "admins: read self" on public.admins;
create policy "admins: read self" on public.admins
  for select using (user_id = auth.uid());
-- admins への追加・削除は SQL Editor（サービスロール）からのみ行います

drop policy if exists "contrib: read approved, own, or admin" on public.contributions;
drop policy if exists "contrib: insert own"                    on public.contributions;
drop policy if exists "contrib: admin update"                  on public.contributions;
drop policy if exists "contrib: delete own pending or admin"   on public.contributions;
create policy "contrib: read approved, own, or admin" on public.contributions
  for select using (status = 'approved' or author_id = auth.uid() or public.is_admin());
create policy "contrib: insert own" on public.contributions
  for insert to authenticated with check (author_id = auth.uid());
create policy "contrib: admin update" on public.contributions
  for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy "contrib: delete own pending or admin" on public.contributions
  for delete to authenticated using ((author_id = auth.uid() and status = 'pending') or public.is_admin());

-- ---------- 運営者の登録（初回のみ・手動） ----------
-- 1) サイトで一度 Google ログイン（またはメール登録）してから、
-- 2) 下の行のメールアドレスを自分のものに書き換えて実行してください。
--
-- insert into public.admins (user_id)
--   select id from auth.users where email = 'YOUR_EMAIL@example.com'
--   on conflict do nothing;
