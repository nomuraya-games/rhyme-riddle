"""
なぞなぞ画像生成モジュール

目的:
    Pillowを使ってなぞなぞの問題文を画像化する。
    扉絵（タイトル画像）と問題画像を生成する。

使い方:
    uv run image.py --question "カメはカメでも、首が長いカメはなーんだ？" --output riddle.png
"""

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 画像サイズ（はてなブログ推奨: 横長）
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 450

# カラーパレット
BG_COLOR = "#FFF9F0"       # 温かみのある白
BORDER_COLOR = "#E8A87C"   # オレンジ系
TEXT_COLOR = "#333333"     # ダークグレー
ACCENT_COLOR = "#D35400"   # 濃いオレンジ（タイトル用）
SHADOW_COLOR = "#DDDDDD"   # シャドウ

# フォントパス（macOS）
FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
FONT_PATH_LIGHT = "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc"


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """フォントをロードする。失敗時はデフォルトフォントにフォールバック。"""
    path = FONT_PATH_LIGHT if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        return ImageFont.load_default()


def draw_rounded_rect(draw: ImageDraw.Draw, xy: tuple, radius: int, fill: str, outline: str = None, width: int = 1):
    """角丸矩形を描画する。"""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)


def create_question_image(question: str, output_path: str = "riddle_question.png") -> str:
    """
    なぞなぞの問題文を画像化する。

    Args:
        question: 問題文（「XはXでも...はなーんだ？」）
        output_path: 出力ファイルパス

    Returns:
        保存したファイルパス
    """
    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 外枠
    draw_rounded_rect(
        draw,
        (20, 20, IMAGE_WIDTH - 20, IMAGE_HEIGHT - 20),
        radius=20,
        fill=BG_COLOR,
        outline=BORDER_COLOR,
        width=4,
    )

    # タイトルラベル
    title_font = load_font(28, bold=True)
    title_text = "なぞなぞ"
    draw_rounded_rect(
        draw,
        (60, 45, 200, 90),
        radius=10,
        fill=ACCENT_COLOR,
    )
    draw.text((80, 52), title_text, font=title_font, fill="white")

    # 問題文（折り返し処理）
    question_font = load_font(38)
    max_chars = 18
    lines = textwrap.wrap(question, width=max_chars)

    total_height = len(lines) * 55
    start_y = (IMAGE_HEIGHT - total_height) // 2 + 10

    for i, line in enumerate(lines):
        y = start_y + i * 55
        # シャドウ
        draw.text((62, y + 2), line, font=question_font, fill=SHADOW_COLOR)
        # 本文
        draw.text((60, y), line, font=question_font, fill=TEXT_COLOR)

    # 下部装飾
    draw.line(
        [(60, IMAGE_HEIGHT - 60), (IMAGE_WIDTH - 60, IMAGE_HEIGHT - 60)],
        fill=BORDER_COLOR,
        width=2,
    )
    hint_font = load_font(22)
    draw.text((60, IMAGE_HEIGHT - 50), "答えはわかるかな？", font=hint_font, fill=ACCENT_COLOR)

    img.save(output_path)
    print(f"問題画像を保存しました: {output_path}")
    return output_path


def create_cover_image(title: str = "なぞなぞチャレンジ！", output_path: str = "riddle_cover.png") -> str:
    """
    扉絵（ブログ記事のサムネイル）を生成する。

    Args:
        title: 扉絵のタイトル
        output_path: 出力ファイルパス

    Returns:
        保存したファイルパス
    """
    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), ACCENT_COLOR)
    draw = ImageDraw.Draw(img)

    # 背景グラデーション風（横ストライプ）
    for y in range(IMAGE_HEIGHT):
        ratio = y / IMAGE_HEIGHT
        r = int(211 + (255 - 211) * ratio * 0.3)
        g = int(84 + (200 - 84) * ratio * 0.2)
        b = int(0 + 50 * ratio * 0.3)
        draw.line([(0, y), (IMAGE_WIDTH, y)], fill=(r, g, b))

    # 中央パネル
    draw_rounded_rect(
        draw,
        (80, 100, IMAGE_WIDTH - 80, IMAGE_HEIGHT - 100),
        radius=25,
        fill="#FFFFFF",
        outline="#FFD700",
        width=5,
    )

    # タイトル
    title_font = load_font(52, bold=True)
    lines = textwrap.wrap(title, width=14)
    total_height = len(lines) * 70
    start_y = (IMAGE_HEIGHT - total_height) // 2 - 10

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        text_width = bbox[2] - bbox[0]
        x = (IMAGE_WIDTH - text_width) // 2
        y = start_y + i * 70
        draw.text((x + 2, y + 2), line, font=title_font, fill=SHADOW_COLOR)
        draw.text((x, y), line, font=title_font, fill=ACCENT_COLOR)

    # 装飾テキスト
    sub_font = load_font(26)
    sub_text = "〜 XはXでも 〜"
    bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_width = bbox[2] - bbox[0]
    draw.text(
        ((IMAGE_WIDTH - sub_width) // 2, IMAGE_HEIGHT - 130),
        sub_text,
        font=sub_font,
        fill=ACCENT_COLOR,
    )

    img.save(output_path)
    print(f"扉絵を保存しました: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="なぞなぞ画像生成")
    subparsers = parser.add_subparsers(dest="command")

    # 問題画像
    q_parser = subparsers.add_parser("question", help="問題画像を生成")
    q_parser.add_argument("--question", required=True, help="問題文")
    q_parser.add_argument("--output", default="riddle_question.png", help="出力ファイル名")

    # 扉絵
    c_parser = subparsers.add_parser("cover", help="扉絵を生成")
    c_parser.add_argument("--title", default="なぞなぞチャレンジ！", help="タイトル")
    c_parser.add_argument("--output", default="riddle_cover.png", help="出力ファイル名")

    args = parser.parse_args()

    if args.command == "question":
        create_question_image(args.question, args.output)
    elif args.command == "cover":
        create_cover_image(args.title, args.output)
    else:
        # デモ: 両方生成
        create_cover_image()
        create_question_image("カメはカメでも、首が長いカメはなーんだ？")


if __name__ == "__main__":
    main()
