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
  supabaseUrl: "",        // 例: "https://abcdefghijkl.supabase.co"
  supabaseAnonKey: "",    // 例: "sb_publishable_..."（プロジェクト画面上部の Connect、または Project Settings → API Keys）
  providers: { google: true, email: true },   // ログイン方法（Google 連携 / メール登録）
  supabaseJs: "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"
};
