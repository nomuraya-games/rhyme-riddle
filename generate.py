"""
なぞなぞ生成モジュール

目的:
    Groq APIを使って「XはXでも〇〇なXはなーんだ？」形式の
    ライミングなぞなぞを生成する。

使い方:
    uv run generate.py
    uv run generate.py --count 3
"""

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _get_api_key() -> str | None:
    """環境変数 → vault の順でGroq APIキーを取得する。"""
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    vault_path = Path.home() / "workspace-ai/nomuraya-shelf/vault/credentials.env"
    if vault_path.exists():
        for line in vault_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


SYSTEM_PROMPT = """あなたは「XはXでも」形式のなぞなぞを作る専門家です。

【形式】
「〇〇は〇〇でも、△△な〇〇はなーんだ？」
答えは別の言葉だが、〇〇の音（韻）を含む言葉になる。

【例】
- 問題: カメはカメでも、首が長いカメはなーんだ？
  答え: カメルーン（カメ＋ルーン）

- 問題: パンはパンでも、食べられないパンはなーんだ？
  答え: フライパン（フライ＋パン）

- 問題: ネコはネコでも、毛がないネコはなーんだ？
  答え: スネコすり（うそ）→ スコティッシュフォールド（うそ）
  ※ 答えは必ず「〇〇」の音を含む別の言葉にすること

【出力形式】
必ずJSON形式で出力すること。他の文字は含めない。
{
  "riddles": [
    {
      "question": "〇〇は〇〇でも、△△な〇〇はなーんだ？",
      "answer": "答え",
      "explanation": "なぜその答えになるか（ライミングの解説）"
    }
  ]
}
"""


def generate_riddles(count: int = 1) -> list[dict]:
    """
    なぞなぞを生成する。

    Args:
        count: 生成するなぞなぞの数

    Returns:
        なぞなぞのリスト（question, answer, explanation を含む辞書）
    """
    api_key = _get_api_key()
    if not api_key:
        print("エラー: GROQ_API_KEY が見つかりません", file=sys.stderr)
        print("~/.zshrc か vault/credentials.env に設定してください", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

    user_message = f"「XはXでも」形式のなぞなぞを{count}問作ってください。"

    print(f"なぞなぞを{count}問生成中... (model: {GROQ_MODEL})", file=sys.stderr)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    response_text = response.choices[0].message.content
    print(f"APIレスポンス:\n{response_text}", file=sys.stderr)

    data = json.loads(response_text)
    return data["riddles"]


def main():
    parser = argparse.ArgumentParser(description="なぞなぞジェネレータ")
    parser.add_argument("--count", type=int, default=1, help="生成するなぞなぞの数（デフォルト: 1）")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    riddles = generate_riddles(count=args.count)

    if args.json:
        print(json.dumps({"riddles": riddles}, ensure_ascii=False, indent=2))
    else:
        for i, riddle in enumerate(riddles, 1):
            print(f"\n【なぞなぞ {i}】")
            print(f"問題: {riddle['question']}")
            print(f"答え: {riddle['answer']}")
            print(f"解説: {riddle['explanation']}")


if __name__ == "__main__":
    main()
