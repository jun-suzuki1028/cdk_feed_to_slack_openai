import openai
import feedparser
import json
import requests
from typing import List, Dict
from datetime import datetime, timedelta, timezone
import os

# タイムゾーンを日本時間に設定
JST = timezone(timedelta(hours=+9))

# APIキーの設定
openai.api_key = os.environ["OPENAI_API_KEY"]

# Slack Webhook URL
WEBHOOK_URL = "https://hooks.slack.com/services/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"  # noqa E501

# OpenAI API モデル名
OPENAI_MODEL: str = "gpt-3.5-turbo"

# RSSフィードURL(DevelopersIO)
FEED_URL = "https://dev.classmethod.jp/feed/"

SYSTEM_PARAMETER = """```
与えられたフィードの情報を、以下の制約条件をもとに要約を出力してください。

制約条件:
・文章は簡潔にわかりやすく。
・箇条書きで3行で出力。
・要約した文章は日本語へ翻訳。
・最終的な結論を含めること。

期待する出力フォーマット:
1.
2.
3.
```"""


def get_feed_entries() -> List[Dict]:
    """
    RSSフィードの取得し、過去1時間以内の更新のみを取得する
    """
    updated_since = datetime.now(JST) - timedelta(hours=2)
    # RSSフィードの取得
    feed = feedparser.parse(FEED_URL)
    # 更新日時の閾値よりも新しいエントリーのみを取得
    new_entries: List[Dict] = [
        entry for entry in feed.entries
        if datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        .astimezone(JST) > updated_since
    ]

    return new_entries


def generate_summary(feed) -> str:
    """
    RSSフィードを元に、OpenAIで要約を実行
    """
    text = f"{feed.title}>\n{feed.summary}"
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PARAMETER},
            {"role": "user", "content": text},
        ],
        temperature=0.25,
    )
    summary: str = response.choices[0]["message"]["content"].strip()
    return summary


def post_to_slack(message: str, link_url: str, title: str) -> None:
    """
    RSSフィードとOpenAIの要約SlackのWebhookURLへPOST
    """
    data = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{link_url}|{title}>",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
            {"type": "divider"},
        ],
        "unfurl_links": False,
    }
    requests.post(WEBHOOK_URL, data=json.dumps(data))


def handler() -> None:

    # RSSフィードから記事を取得し、要約を生成してSlackに投稿する
    for entry in get_feed_entries():
        summary: str = generate_summary(entry)

        post_to_slack(summary, entry.link, entry.title)


if __name__ == "__main__":
    handler()
