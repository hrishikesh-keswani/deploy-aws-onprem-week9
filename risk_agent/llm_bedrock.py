"""Amazon Bedrock converse client. Credentials come from the ECS task role."""

from __future__ import annotations

import os

DEFAULT_MODEL_ID = "us.amazon.nova-lite-v1:0"


class BedrockClient:
    def __init__(self, model_id: str = None, region: str = None) -> None:
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        self.region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

    def chat(self, system: str, user: str) -> tuple:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=self.region)
        response = client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"temperature": 0, "maxTokens": 400},
        )
        parts = response.get("output", {}).get("message", {}).get("content") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        usage = response.get("usage") or {}
        prompt_tokens = int(usage.get("inputTokens") or 0)
        completion_tokens = int(usage.get("outputTokens") or 0)
        return text, prompt_tokens, completion_tokens
