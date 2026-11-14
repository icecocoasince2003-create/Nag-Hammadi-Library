-- =====================================================================
--  ナグ・ハマディ写本コーパス — コミュニティ機能
--    * コメント・注釈・誤りの指摘（承認制）と、投稿者による修正
--    * プロフィール（表示名・ブックマーク・運営へのメッセージ）
--  Supabase (PostgreSQL) スキーマ。Supabase ダッシュボードの SQL Editor に
--  このファイル全体を貼り付けて実行してください（再実行しても安全です）。
--  ★ このファイルを更新したときは、もう一度全体を貼り付けて実行すると、
--    足りないテーブル・関数・権限だけが追加されます（既存のデータは消えません）。
--
--  方針
--   * 投稿はすべて status = 'pending'（承認待ち）で保存され、運営（admins）が
--     承認したものだけが一般公開されます。
--   * 投稿者は自分の投稿を状態にかかわらず閲覧でき、承認前なら削除・修正できます。
--     公開済みの投稿の修正は「修正の申請」として保存され、運営が承認すると反映されます
--     （承認されるまでは、公開中の内容がそのまま表示されます）。
--   * 運営かどうかは admins テーブルで管理します（末尾の「運営者の登録」参照）。
--   * メールアドレスは公開されません（公開されるのは表示名のみ）。
--   * ブックマークは本人だけが、運営へのメッセージは本人と運営だけが読めます。
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
alter table public.contributions add column if not exists updated_at timestamptz;   -- 投稿者が最後に修正した日時
create index if not exists contributions_doc_idx    on public.contributions (doc, status);
create index if not exists contributions_status_idx on public.contributions (status, created_at);
create index if not exists contributions_author_idx on public.contributions (author_id, created_at);

-- ---------- 公開済みの投稿への「修正の申請」 ----------
-- 1 つの投稿につき 1 件。運営が承認すると投稿に反映されて行は消え、
-- 却下すると status = 'rejected' とメモが残ります（投稿者本人にだけ表示）。
-- 書き込みは下の関数 edit_contribution / review_revision からのみ行います。
create table if not exists public.contribution_revisions (
  contribution_id bigint primary key references public.contributions (id) on delete cascade,
  author_id       uuid not null references auth.users (id) on delete cascade,
  kind            public.contribution_kind not null,
  body            text not null check (char_length(btrim(body)) between 1 and 4000),
  suggestion      text check (suggestion is null or char_length(suggestion) <= 1000),
  status          public.contribution_status not null default 'pending' check (status in ('pending', 'rejected')),
  moderator_note  text check (moderator_note is null or char_length(moderator_note) <= 2000),
  created_at      timestamptz not null default now(),
  reviewed_at     timestamptz
);
create index if not exists contribution_revisions_status_idx on public.contribution_revisions (status, created_at);

-- ---------- ブックマーク（文書または本文のセグメント） ----------
create table if not exists public.bookmarks (
  id         bigint generated always as identity primary key,
  user_id    uuid not null default auth.uid() references auth.users (id) on delete cascade,
  doc        text not null check (doc ~ '^[a-z0-9_-]{1,40}$'),
  witness    text check (witness is null or witness ~ '^[A-Za-z0-9_-]{1,20}$'),   -- 追加したときに開いていた写本（リンク用）
  seg_id     text check (seg_id is null or char_length(seg_id) between 1 and 80),  -- null = 文書全体
  seg_label  text check (seg_label is null or char_length(seg_label) <= 40),
  excerpt    text check (excerpt is null or char_length(excerpt) <= 200),          -- 一覧に出す本文の冒頭
  note       text check (note is null or char_length(note) <= 500),                -- 本人のメモ
  created_at timestamptz not null default now()
);
-- 同じ箇所は 1 人 1 件まで
create unique index if not exists bookmarks_target_idx on public.bookmarks (user_id, doc, coalesce(seg_id, ''));

-- ---------- 運営へのメッセージ（バグの報告・応援メッセージ） ----------
do $$ begin
  create type public.feedback_kind as enum ('bug', 'cheer');
exception when duplicate_object then null; end $$;
do $$ begin
  create type public.feedback_status as enum ('new', 'done');
exception when duplicate_object then null; end $$;

create table if not exists public.feedback (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  author_name text,
  kind        public.feedback_kind not null,
  body        text not null check (char_length(btrim(body)) between 1 and 4000),
  page        text check (page is null or char_length(page) <= 300),              -- 問題が起きたページ（任意）
  user_agent  text check (user_agent is null or char_length(user_agent) <= 400),  -- ブラウザの種類（本人が添付を選んだ場合のみ）
  status      public.feedback_status not null default 'new',
  reply       text check (reply is null or char_length(reply) <= 2000),            -- 運営からの返信（本人にだけ表示）
  created_at  timestamptz not null default now(),
  handled_at  timestamptz
);
create index if not exists feedback_status_idx on public.feedback (status, created_at);
create index if not exists feedback_user_idx   on public.feedback (user_id, created_at);

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

-- ---------- 表示名を変えたら、過去の投稿・メッセージの表示名も合わせる ----------
create or replace function public.profiles_before_update()
returns trigger language plpgsql set search_path = public as $$
begin
  new.id := old.id;
  new.created_at := old.created_at;
  new.display_name := btrim(new.display_name);
  return new;
end $$;
drop trigger if exists profiles_bu on public.profiles;
create trigger profiles_bu before update on public.profiles
  for each row execute function public.profiles_before_update();

create or replace function public.profiles_after_update()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.display_name is distinct from old.display_name then
    update public.contributions set author_name = new.display_name where author_id = new.id;
    update public.feedback      set author_name = new.display_name where user_id   = new.id;
  end if;
  return null;
end $$;
drop trigger if exists profiles_au on public.profiles;
create trigger profiles_au after update on public.profiles
  for each row execute function public.profiles_after_update();

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
  new.updated_at  := null;
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

-- 更新時の制限。
--   サイト（API）から直接行う更新は、Supabase のロール anon / authenticated として実行されます。
--   その場合に変えられるのは「状態」と「運営メモ」だけ（＝運営による承認・却下）で、
--   本文・種類・修正案・投稿者・日時は、運営であっても直接は書き換えられません。
--   本文が変わるのは、投稿者本人の修正を扱う関数（下の edit_contribution / review_revision）と
--   表示名の同期（上の profiles_after_update）だけです。これらは security definer の関数なので
--   このトリガーの中では current_user が関数の所有者になり、制限の対象から外れます
--   （SQL Editor からの手作業の修正も同じ扱いです）。
create or replace function public.contributions_before_update()
returns trigger language plpgsql security invoker set search_path = public as $$
begin
  if current_user in ('anon', 'authenticated') then
    new.author_id   := old.author_id;
    new.author_name := old.author_name;
    new.kind        := old.kind;
    new.body        := old.body;
    new.suggestion  := old.suggestion;
    new.created_at  := old.created_at;
    new.updated_at  := old.updated_at;
    if new.status is distinct from old.status then
      new.reviewed_at := now();
      new.reviewed_by := auth.uid();
    else
      new.reviewed_at := old.reviewed_at;
      new.reviewed_by := old.reviewed_by;
    end if;
  end if;
  return new;
end $$;
drop trigger if exists contributions_bu on public.contributions;
create trigger contributions_bu before update on public.contributions
  for each row execute function public.contributions_before_update();

-- 公開をやめた投稿（approved → それ以外）に残っている修正の申請は破棄する
create or replace function public.contributions_after_update()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if old.status = 'approved' and new.status <> 'approved' then
    delete from public.contribution_revisions where contribution_id = new.id;
  end if;
  return null;
end $$;
drop trigger if exists contributions_au on public.contributions;
create trigger contributions_au after update on public.contributions
  for each row execute function public.contributions_after_update();

-- ---------- 投稿者による修正 ----------
--   承認待ち・非公開（却下）の投稿 … その場で書き換えて、承認待ちに戻す          → 'pending'
--   公開済みの投稿               … 修正の申請として保存（公開中の内容はそのまま）  → 'revision'
--                                   公開中の内容と同じなら申請を取り下げる          → 'unchanged'
create or replace function public.edit_contribution(
  p_id bigint, p_kind public.contribution_kind, p_body text, p_suggestion text default null)
returns text language plpgsql security definer set search_path = public as $$
declare
  c         public.contributions%rowtype;
  v_kind    public.contribution_kind;
  v_body    text := btrim(coalesce(p_body, ''));
  v_sugg    text := nullif(btrim(coalesce(p_suggestion, '')), '');
  n_pending int;
begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  select * into c from public.contributions where id = p_id and author_id = auth.uid() for update;
  if not found then raise exception 'contribution not found'; end if;
  v_kind := coalesce(p_kind, c.kind);
  if char_length(v_body) < 1 or char_length(v_body) > 4000 then
    raise exception 'body must be 1 to 4000 characters';
  end if;
  if v_kind <> 'correction' then v_sugg := null; end if;     -- 修正案は「誤りの指摘」だけが持つ
  if char_length(v_sugg) > 1000 then raise exception 'suggestion must be at most 1000 characters'; end if;

  if c.status = 'approved' then
    if v_kind = c.kind and v_body = c.body and v_sugg is not distinct from c.suggestion then
      delete from public.contribution_revisions where contribution_id = c.id;
      return 'unchanged';
    end if;
    insert into public.contribution_revisions
      (contribution_id, author_id, kind, body, suggestion, status, moderator_note, created_at, reviewed_at)
    values (c.id, c.author_id, v_kind, v_body, v_sugg, 'pending', null, now(), null)
    on conflict (contribution_id) do update
      set kind = excluded.kind, body = excluded.body, suggestion = excluded.suggestion,
          status = 'pending', moderator_note = null, created_at = excluded.created_at, reviewed_at = null;
    return 'revision';
  end if;

  if c.status = 'rejected' then      -- 再申請: 承認待ちの上限（30 件）は新規投稿と同じ
    select count(*) into n_pending from public.contributions
      where author_id = auth.uid() and status = 'pending';
    if n_pending >= 30 then raise exception 'too many pending contributions'; end if;
  end if;
  -- 前回の却下時の運営メモは消す（書き直した内容に対するメモではないため）
  update public.contributions
     set kind = v_kind, body = v_body, suggestion = v_sugg, status = 'pending',
         moderator_note = null, reviewed_at = null, reviewed_by = null, updated_at = now()
   where id = c.id;
  return 'pending';
end $$;
revoke execute on function public.edit_contribution(bigint, public.contribution_kind, text, text) from public, anon;
grant  execute on function public.edit_contribution(bigint, public.contribution_kind, text, text) to authenticated;

-- ---------- 運営による「修正の申請」の承認・却下 ----------
create or replace function public.review_revision(p_id bigint, p_approve boolean, p_note text default null)
returns void language plpgsql security definer set search_path = public as $$
declare r public.contribution_revisions%rowtype;
begin
  if not public.is_admin() then raise exception 'not allowed'; end if;
  select * into r from public.contribution_revisions
    where contribution_id = p_id and status = 'pending' for update;
  if not found then raise exception 'revision not found'; end if;
  if p_approve then
    update public.contributions
       set kind = r.kind, body = r.body, suggestion = r.suggestion,
           updated_at = r.created_at, reviewed_at = now(), reviewed_by = auth.uid()
     where id = p_id and status = 'approved';
    if not found then raise exception 'contribution is not published'; end if;
    delete from public.contribution_revisions where contribution_id = p_id;
  else
    update public.contribution_revisions
       set status = 'rejected', moderator_note = nullif(btrim(coalesce(p_note, '')), ''), reviewed_at = now()
     where contribution_id = p_id;
  end if;
end $$;
revoke execute on function public.review_revision(bigint, boolean, text) from public, anon;
grant  execute on function public.review_revision(bigint, boolean, text) to authenticated;

-- ---------- ブックマーク: 1 人 500 件まで ----------
create or replace function public.bookmarks_before_insert()
returns trigger language plpgsql security definer set search_path = public as $$
declare n int;
begin
  new.user_id    := auth.uid();
  new.created_at := now();
  select count(*) into n from public.bookmarks where user_id = auth.uid();
  if n >= 500 then raise exception 'too many bookmarks'; end if;
  return new;
end $$;
drop trigger if exists bookmarks_bi on public.bookmarks;
create trigger bookmarks_bi before insert on public.bookmarks
  for each row execute function public.bookmarks_before_insert();

-- ---------- 運営へのメッセージ: 送信時の正規化（1 人 24 時間に 20 件まで） ----------
create or replace function public.feedback_before_insert()
returns trigger language plpgsql security definer set search_path = public as $$
declare n int;
begin
  new.user_id    := auth.uid();
  new.status     := 'new';
  new.reply      := null;
  new.handled_at := null;
  new.created_at := now();
  select display_name into new.author_name from public.profiles where id = auth.uid();
  select count(*) into n from public.feedback
    where user_id = auth.uid() and created_at > now() - interval '24 hours';
  if n >= 20 then raise exception 'too many messages'; end if;
  return new;
end $$;
drop trigger if exists feedback_bi on public.feedback;
create trigger feedback_bi before insert on public.feedback
  for each row execute function public.feedback_before_insert();

-- 運営が変えられるのは「状態」と「返信」だけ（本文は書き換えない）
create or replace function public.feedback_before_update()
returns trigger language plpgsql security invoker set search_path = public as $$
begin
  if current_user in ('anon', 'authenticated') then
    new.user_id     := old.user_id;
    new.author_name := old.author_name;
    new.kind        := old.kind;
    new.body        := old.body;
    new.page        := old.page;
    new.user_agent  := old.user_agent;
    new.created_at  := old.created_at;
  end if;
  if new.status is distinct from old.status then
    new.handled_at := case when new.status = 'done' then now() else null end;
  end if;
  return new;
end $$;
drop trigger if exists feedback_bu on public.feedback;
create trigger feedback_bu before update on public.feedback
  for each row execute function public.feedback_before_update();

-- ---------- 行レベルセキュリティ ----------
alter table public.profiles               enable row level security;
alter table public.admins                 enable row level security;
alter table public.contributions          enable row level security;
alter table public.contribution_revisions enable row level security;
alter table public.bookmarks              enable row level security;
alter table public.feedback               enable row level security;

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
drop policy if exists "contrib: delete own unpublished or admin" on public.contributions;
create policy "contrib: read approved, own, or admin" on public.contributions
  for select using (status = 'approved' or author_id = auth.uid() or public.is_admin());
create policy "contrib: insert own" on public.contributions
  for insert to authenticated with check (author_id = auth.uid());
create policy "contrib: admin update" on public.contributions
  for update to authenticated using (public.is_admin()) with check (public.is_admin());
-- 投稿者が自分で取り消せるのは、公開されていない投稿（承認待ち・非公開）だけ
create policy "contrib: delete own unpublished or admin" on public.contributions
  for delete to authenticated
  using ((author_id = auth.uid() and status in ('pending', 'rejected')) or public.is_admin());

-- 修正の申請: 読めるのは本人と運営。取り下げ（削除）も本人と運営。追加・変更は関数からのみ
drop policy if exists "revisions: read own or admin"   on public.contribution_revisions;
drop policy if exists "revisions: delete own or admin" on public.contribution_revisions;
create policy "revisions: read own or admin" on public.contribution_revisions
  for select to authenticated using (author_id = auth.uid() or public.is_admin());
create policy "revisions: delete own or admin" on public.contribution_revisions
  for delete to authenticated using (author_id = auth.uid() or public.is_admin());

-- ブックマーク: 本人だけ
drop policy if exists "bookmarks: own" on public.bookmarks;
create policy "bookmarks: own" on public.bookmarks
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 運営へのメッセージ: 読めるのは本人と運営。送信は本人、状態と返信の更新は運営、削除は本人と運営
drop policy if exists "feedback: read own or admin"   on public.feedback;
drop policy if exists "feedback: insert own"          on public.feedback;
drop policy if exists "feedback: admin update"        on public.feedback;
drop policy if exists "feedback: delete own or admin" on public.feedback;
create policy "feedback: read own or admin" on public.feedback
  for select to authenticated using (user_id = auth.uid() or public.is_admin());
create policy "feedback: insert own" on public.feedback
  for insert to authenticated with check (user_id = auth.uid());
create policy "feedback: admin update" on public.feedback
  for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy "feedback: delete own or admin" on public.feedback
  for delete to authenticated using (user_id = auth.uid() or public.is_admin());

-- ---------- テーブルの権限（行レベルセキュリティと併用） ----------
grant select, delete                 on public.contribution_revisions to authenticated;
grant select, insert, update, delete on public.bookmarks              to authenticated;
grant select, insert, update, delete on public.feedback               to authenticated;

-- ---------- API（PostgREST）に、追加したテーブルと関数をすぐ認識させる ----------
notify pgrst, 'reload schema';

-- ---------- 運営者の登録（初回のみ・手動） ----------
-- 1) サイトで一度 Google ログイン（またはメール登録）してから、
-- 2) 下の行のメールアドレスを自分のものに書き換えて実行してください。
--
-- insert into public.admins (user_id)
--   select id from auth.users where email = 'YOUR_EMAIL@example.com'
--   on conflict do nothing;
