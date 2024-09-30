"""AI services."""

import json
import re

from django.conf import settings

from openai import OpenAI
from rest_framework import serializers

from core import enums

AI_ACTIONS = {
    "prompt": (
        "Answer the prompt in markdown format. Return JSON: "
        '{"answer": "Your markdown answer"}. '
        "Do not provide any other information."
    ),
    "correct": (
        "Correct grammar and spelling of the markdown text, "
        "preserving language and markdown formatting. "
        'Return JSON: {"answer": "your corrected markdown text"}. '
        "Do not provide any other information."
    ),
    "rephrase": (
        "Rephrase the given markdown text, "
        "preserving language and markdown formatting. "
        'Return JSON: {"answer": "your rephrased markdown text"}. '
        "Do not provide any other information."
    ),
    "summarize": (
        "Summarize the markdown text, preserving language and markdown formatting. "
        'Return JSON: {"answer": "your markdown summary"}. '
        "Do not provide any other information."
    ),
}

AI_TRANSLATE = (
    "Translate the markdown text to {language:s}, preserving markdown formatting. "
    'Return JSON: {{"answer": "your translated markdown text in {language:s}"}}. '
    "Do not provide any other information."
)


class AIService:
    """Service class for AI-related operations."""

    def __init__(self):
        """Ensure that the AI configuration is set properly."""
        if (
            settings.AI_BASE_URL is None
            or settings.AI_API_KEY is None
            or settings.AI_MODEL is None
        ):
            raise serializers.ValidationError("AI configuration not set")
        self.client = OpenAI(base_url=settings.AI_BASE_URL, api_key=settings.AI_API_KEY)

    def transform(self, text, action):
        """Call the OpenAI API with the transform prompt and return the response."""
        system_content = AI_ACTIONS[action]
        response = self.client.chat.completions.create(
            model=settings.AI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": json.dumps({"markdown_input": text})},
            ],
        )

        content = response.choices[0].message.content
        sanitized_content = re.sub(r"(?<!\\)\n", "\\\\n", content)
        sanitized_content = re.sub(r"(?<!\\)\t", "\\\\t", sanitized_content)

        json_response = json.loads(sanitized_content)

        if "answer" not in json_response:
            raise RuntimeError("AI response does not contain an answer")

        return json_response

    def translate(self, text, language):
        """Call the OpenAI API with the transform prompt and return the response."""
        language_display = enums.ALL_LANGUAGES.get(language, language)
        system_content = AI_TRANSLATE.format(language=language_display)
        response = self.client.chat.completions.create(
            model=settings.AI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": json.dumps({"markdown_input": text})},
            ],
        )

        content = response.choices[0].message.content
        sanitized_content = re.sub(r"(?<!\\)\n", "\\\\n", content)
        sanitized_content = re.sub(r"(?<!\\)\t", "\\\\t", sanitized_content)

        json_response = json.loads(sanitized_content)

        if "answer" not in json_response:
            raise RuntimeError("AI response does not contain an answer")

        return json_response
