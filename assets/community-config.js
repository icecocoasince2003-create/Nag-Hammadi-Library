/* ============================================================
   community-config.js — コメント・注釈機能の接続設定
   Supabase プロジェクトを作成したら、下の 2 項目を書き換えてください
   （手順は docs/COMMUNITY_SETUP.md）。空のままだと機能は表示されません。

   ※ Publishable key（sb_publishable_…）／旧形式の anon key は「公開してよい鍵」です
     （行レベルセキュリティで保護されます）。Secret key・service_role key は絶対にここへ書かないでください。

   動作確認だけしたいときは、任意のページの URL に ?community=demo を付けると
   ブラウザ内だけで動くデモモードになります（?community=off で解除）。
   ============================================================ */
window.NHC_COMMUNITY_CONFIG = {
  supabaseUrl: "https://ngzzklrjbkzsnegozpps.supabase.co",
  supabaseAnonKey: "sb_publishable__9_fU-JrN7-IVd8dBsPQ-A_E5bIriZR",
  providers: { google: true, email: true },
  // Supabase のライブラリ（supabase-js）。正確な版に固定し、ファイルが変わっていないことを確かめるハッシュ（SRI）を添える。
  // 版を上げるときは URL とハッシュを一緒に変える（README「外部のスクリプトの版とハッシュ」）
  supabaseJs: "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.119.2/dist/umd/supabase.js",
  supabaseJsIntegrity: "sha384-A97u3Qnt9GZHURO9YJZRe7VQgGUeFzcv6I1oIGnUTxQrCxnpQMwR0/G8F2zt9abZ"
};
