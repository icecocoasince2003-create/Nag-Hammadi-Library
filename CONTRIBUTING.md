# 共同編集ガイド（CONTRIBUTING）

このリポジトリはナグ・ハマディ写本コーパスの TEI データと公開サイトを管理しています。
共同編集者（Collaborator）として招待を受けた方は、以下の流れで作業してください。

## 0. 前提

- GitHub アカウントを持ち、リポジトリのオーナーから Collaborator 招待を受けていること
  （メールまたは GitHub の通知から **Accept invitation** を押す）
- Git と Python 3 がインストールされていること

## 1. 初回セットアップ（1回だけ）

```bash
git clone https://github.com/<オーナー名>/<リポジトリ名>.git
cd <リポジトリ名>
```

動作確認として一度ビルドを実行:

```bash
python3 scripts/build_tei.py
```

末尾に `segments: ... | tokens: ...` の統計が表示されれば環境は OK です。

## 2. ふだんの編集サイクル

```bash
# (1) 最新を取り込む — 作業開始前に必ず実行
git switch main
git pull origin main

# (2) 作業用ブランチを切る — main に直接コミットしない
git switch -c fix/lexicon-typo-20260704
#   ブランチ名の例: fix/…（修正） add/…（追加） trans/…（対訳） notes/…（注釈）

# (3) source/ の CSV を編集する（詳細は source/README.md）

# (4) XML を再生成し、エラーがないことを確認
python3 scripts/build_tei.py
#   目次(index.html)に関わる変更をした場合のみ:
#   python3 scripts/build_site.py

# (5) ブラウザでローカル確認（fetch を使うためローカルサーバが必要）
python3 -m http.server 8000
#   → http://localhost:8000 を開いて表示を確認

# (6) コミットして push
git add source/ data/ index.html tractate.html
git commit -m "lexicon: ϣⲁϫⲉ の語義を修正"
git push -u origin fix/lexicon-typo-20260704
```

## 3. Pull Request（PR）とレビュー

1. push すると GitHub 上に「Compare & pull request」ボタンが出るので押す
2. 変更内容の要約を書いて **Create pull request**
3. レビュー担当（オーナー）が内容を確認し、必要ならコメントで修正依頼
4. 承認されたら **Merge pull request** で main に統合
5. マージ後、GitHub Pages が自動で再デプロイされ、数分でサイトに反映

### PR のルール

- **1つの PR は1つの目的に絞る**（辞書の修正と注釈の追加を混ぜない）
- 生成物（`data/*.xml`, `index.html`, `tractate.html`）は必ず**再生成した状態で**含める
  — サイトは GitHub Pages がリポジトリの内容をそのまま配信するため、生成物もコミットが必要です
- `eugnostos_source.tsv`（本文）と HTML ビュワー本体（`eugnostos.html` 等）の変更は影響が大きいので、PR の説明に理由を明記してください

## 4. コンフリクト（競合）が起きたら

`data/` の XML は自動生成物なので、競合したら**手で直さず再生成**します:

```bash
git switch 自分のブランチ
git pull origin main          # 競合発生
# source/ の CSV の競合だけをエディタで解決する
python3 scripts/build_tei.py  # data/ を作り直す（XML の競合はこれで解消）
git add -A && git commit
```

## 5. やってはいけないこと

- `main` への直接 push（ブランチ → PR を必ず経由する）
- `data/` の XML や `index.html` の直接編集（次のビルドで消えます）
- CSV の ID 列（`seg_id`, `id`, `lemma`）の変更（リンクが壊れます）
- Excel での保存時に文字コードを Shift-JIS にすること（必ず UTF-8）

## フォルダの見取り図

```
├── source/     ← ★編集するのはここ（CSV）。詳細は source/README.md
├── scripts/    ← ビルドスクリプト（通常触らない）
├── data/       ← 自動生成 XML（直接編集しない）
├── image/      ← アイコン等
├── *.html      ← 公開ページ（index / tractate は自動生成、ビュワーは手作業管理）
└── README.md   ← プロジェクト全体の説明
```
