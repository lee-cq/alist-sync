#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : _webhook.py
@Author     : LeeCQ
@Date-Time  : 2024/3/3 21:47

"""
import os

from httpx import Client


class Webhook:
    def __init__(self, url: str, headers: dict[str, str] = None):
        self.client = Client(base_url=url, headers=headers)

    def send(self, data: str):
        return self.client.post(
            "",
            json={
                "msg_type": "text",
                "content": {"text":data},
            },
        )


if __name__ == "__main__":
    webhook = Webhook(os.getenv("WEBHOOK_URL", ""))
    print(webhook.send("test message.").text)
