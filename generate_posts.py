# generate_posts.py

import os
import datetime
import pathlib
import urllib.parse
import re
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
from pytrends.request import TrendReq

# .env から API キーを読み込む
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 出力用テンプレート
TEMPLATE = """---
title: "{title}"
description: "{title} に関する初心者向けブログ記事です。"
pubDate: "{date}"
---

# {title}

{body}

---

## 関連リンク

- [Amazonで関連商品を見る]({affiliate})
"""

# あなたの Amazon アソシエイトタグ
AMAZON_TAG = "autowritehubai-22"

def pick_keywords(n=3):
    pt = TrendReq(hl="ja-JP", tz=540)
    df = pt.today_searches(pn="JP")
    kws = df.head(n)
    return [kw for kw in kws if len(kw) > 4]

def generate_article(keyword):
    sys_prompt  = "あなたはSEOに詳しい日本人ライターです。"
    user_prompt = (
        f"{keyword} について1200文字程度で初心者向けのブログ記事を書いてください。"
        "h2見出しを4つ作り、最後にまとめを書いてください。"
    )

    # ① 通常モデルで試す
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            max_tokens=1500
        )

    # ② クォータ超過なら無料版モデルで再試行
    except RateLimitError as e1:
        print(f"⚠ クォータ超過、無料版モデルで再試行します: {e1}")
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                max_tokens=1000
            )
        except RateLimitError as e2:
            print(f"⚠ 無料版モデルも超過。プレースホルダ本文を生成します: {e2}")
            body = (
                f"記事生成はクォータ超過のため行えませんでした。\n"
                f"トピック: {keyword}\n"
                f"日付: {datetime.date.today().isoformat()}"
            )
        else:
            body = response.choices[0].message.content.strip()
    else:
        body = response.choices[0].message.content.strip()

    # ——— ここから本文の後処理 ———

    # 1) [H2見出しX] → Markdown の H2 に
    body = re.sub(r'\[H2見出し\d:([^\]]+)\]', r'## \1', body)

    # 2) 句点「。」で改行
    body = body.replace('。', '。\n\n')

    # ————————————————

    date = datetime.date.today().isoformat()
    safe_title = keyword.replace(" ", "-").replace("　", "-")
    filename = f"{date}-{safe_title}.md"
    query = urllib.parse.quote_plus(keyword)
    affiliate_link = f"https://www.amazon.co.jp/s?k={query}&tag={AMAZON_TAG}"

    content = TEMPLATE.format(
        title=keyword,
        body=body,
        affiliate=affiliate_link,
        date=date
    )

    out_path = pathlib.Path("src/content/blog") / filename
    out_path.write_text(content, encoding="utf-8")
    print(f"✅ 生成完了: {filename}")

def main():
    try:
        keywords = pick_keywords()
    except Exception as e:
        print("トレンド取得に失敗、デフォルトテーマで生成します:", e)
        keywords = ["副業 アイデア", "最新 AI ニュース", "節約術 2025"]

    for kw in keywords:
        generate_article(kw)

if __name__ == "__main__":
    main()
