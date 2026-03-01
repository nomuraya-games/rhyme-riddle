"""
はてなブログ投稿モジュール

目的:
    生成したなぞなぞと画像をはてなブログに投稿する。
    認証情報は vault/credentials.env から取得。
    デフォルトは下書き投稿。

使い方:
    # 下書きとして投稿
    uv run publish.py --riddle-json riddle.json

    # 公開して投稿
    uv run publish.py --riddle-json riddle.json --release
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth


def _load_vault() -> dict:
    """vault/credentials.env から認証情報を読み込む。"""
    vault_path = Path.home() / "workspace-ai/nomuraya-shelf/vault/credentials.env"
    result = {}
    if vault_path.exists():
        for line in vault_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result


def _get(key: str, default: str | None = None) -> str | None:
    """環境変数 → vault の順で値を取得する。"""
    vault = _load_vault()
    return os.getenv(key) or vault.get(key) or default


def _create_wsse_header(username: str, api_key: str) -> str:
    """はてなフォトライフ用 WSSE認証ヘッダを作成する。"""
    nonce = secrets.token_bytes(16)
    nonce_b64 = base64.b64encode(nonce).decode("utf-8")
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    digest_input = nonce + created.encode("utf-8") + api_key.encode("utf-8")
    password_digest = base64.b64encode(hashlib.sha1(digest_input).digest()).decode("utf-8")
    return f'UsernameToken Username="{username}", PasswordDigest="{password_digest}", Nonce="{nonce_b64}", Created="{created}"'


def upload_to_fotolife(image_path: str, title: str, user_id: str, api_key: str) -> str | None:
    """
    はてなフォトライフに画像をアップロードする。

    Args:
        image_path: アップロードする画像パス
        title: 画像タイトル
        user_id: はてなユーザーID
        api_key: はてなAPIキー

    Returns:
        はてな記法のimageシンタックス（例: [f:id:xxx:yyyymmddhhmmss:image]）または None
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    entry_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://purl.org/atom/ns#" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <title>{title}</title>
  <content mode="base64" type="image/png">{image_b64}</content>
  <dc:subject>rhyme-riddle</dc:subject>
</entry>"""

    wsse = _create_wsse_header(user_id, api_key)
    response = requests.post(
        "https://f.hatena.ne.jp/atom/post",
        data=entry_xml.encode("utf-8"),
        headers={"Content-Type": "application/xml", "X-WSSE": wsse},
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"hatena": "http://www.hatena.ne.jp/info/xmlns#"}
    syntax_elem = root.find(".//hatena:syntax", ns)
    if syntax_elem is not None:
        print(f"フォトライフアップロード成功: {syntax_elem.text}", file=sys.stderr)
        return syntax_elem.text

    print("フォトライフアップロード失敗（画像なしで継続）", file=sys.stderr)
    return None


def _build_article(riddle: dict, cover_syntax: str | None, question_syntax: str | None) -> tuple[str, str]:
    """
    なぞなぞ記事のタイトルと本文を構築する。

    Args:
        riddle: なぞなぞデータ（question, answer, explanation）
        cover_syntax: 扉絵のはてな記法
        question_syntax: 問題画像のはてな記法

    Returns:
        (タイトル, 本文) のタプル
    """
    question = riddle["question"]
    answer = riddle["answer"]
    explanation = riddle["explanation"]

    title = f"なぞなぞ：{question}"

    cover_section = f"{cover_syntax}\n\n" if cover_syntax else ""
    question_img_section = f"\n\n{question_syntax}" if question_syntax else ""

    content = f"""{cover_section}## 問題

{question}{question_img_section}

## 答え

<details>
<summary>答えはこちら</summary>

**{answer}**

{explanation}

</details>

---

*なぞなぞジェネレーター rhyme-riddle で自動生成しました*
"""
    return title, content


def publish_riddle(riddle: dict, release: bool = False) -> dict | None:
    """
    なぞなぞをはてなブログに投稿する。

    Args:
        riddle: なぞなぞデータ（question, answer, explanation）
        release: True の場合公開、False の場合下書き（デフォルト）

    Returns:
        {'blog_url': str, 'entry_id': str} または None
    """
    user_id = _get("HATENA_USER_ID", "nomuragorou")
    blog_id = _get("HATENA_BLOG_ID", "nomuraya.hatenablog.jp")
    api_key = _get("HATENA_API_KEY")

    if not api_key:
        print("エラー: HATENA_API_KEY が見つかりません", file=sys.stderr)
        print("vault に追加: echo 'HATENA_API_KEY=<key>' >> ~/workspace-ai/nomuraya-shelf/vault/credentials.env", file=sys.stderr)
        sys.exit(1)

    # 画像生成 → フォトライフアップロード
    from image import create_cover_image, create_question_image

    cover_syntax = None
    question_syntax = None

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            cover_path = str(Path(tmpdir) / "cover.png")
            create_cover_image(output_path=cover_path)
            cover_syntax = upload_to_fotolife(cover_path, "なぞなぞ扉絵", user_id, api_key)
        except Exception as e:
            print(f"扉絵アップロードエラー（スキップ）: {e}", file=sys.stderr)

        try:
            question_path = str(Path(tmpdir) / "question.png")
            create_question_image(riddle["question"], output_path=question_path)
            question_syntax = upload_to_fotolife(question_path, f"なぞなぞ問題: {riddle['question'][:20]}", user_id, api_key)
        except Exception as e:
            print(f"問題画像アップロードエラー（スキップ）: {e}", file=sys.stderr)

    title, content = _build_article(riddle, cover_syntax, question_syntax)

    entry_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{title}</title>
  <author><name>{user_id}</name></author>
  <content type="text/x-markdown">{content}</content>
  <updated>{datetime.now(timezone.utc).isoformat()}Z</updated>
  <category term="なぞなぞ" />
  <category term="自動生成" />
  <app:control>
    <app:draft>{"no" if release else "yes"}</app:draft>
  </app:control>
</entry>"""

    api_url = f"https://blog.hatena.ne.jp/{user_id}/{blog_id}/atom/entry"
    auth = HTTPBasicAuth(user_id, api_key)

    print(f"はてなブログに{'公開' if release else '下書き'}投稿中...", file=sys.stderr)
    response = requests.post(
        api_url,
        auth=auth,
        data=entry_xml.encode("utf-8"),
        headers={"Content-Type": "application/atom+xml; charset=utf-8"},
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    link_elem = root.find("atom:link[@rel='alternate']", ns)
    id_elem = root.find("atom:id", ns)

    entry_id = id_elem.text.split("-")[-1] if id_elem is not None else None
    blog_url = link_elem.get("href") if link_elem is not None else None

    print(f"投稿成功: {blog_url}", file=sys.stderr)
    return {"blog_url": blog_url, "entry_id": entry_id}


def main():
    parser = argparse.ArgumentParser(description="はてなブログ投稿")
    parser.add_argument("--riddle-json", required=True, help="なぞなぞJSONファイルパス（generate.py --json の出力）")
    parser.add_argument("--index", type=int, default=0, help="JSONの何番目のなぞなぞを投稿するか（デフォルト: 0）")
    parser.add_argument("--release", action="store_true", help="公開投稿（デフォルトは下書き）")
    args = parser.parse_args()

    with open(args.riddle_json, encoding="utf-8") as f:
        data = json.load(f)

    riddles = data.get("riddles", [data])  # 単一dictにも対応
    if args.index >= len(riddles):
        print(f"エラー: index {args.index} が範囲外です（{len(riddles)}件）", file=sys.stderr)
        sys.exit(1)

    riddle = riddles[args.index]
    result = publish_riddle(riddle, release=args.release)

    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
