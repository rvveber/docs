"""
Test ai API endpoints in the impress core app.
"""

from typing import List
from unittest.mock import patch

from django.test.utils import override_settings

import pytest
from pydantic import BaseModel
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from core import factories

pytestmark = pytest.mark.django_db


class MessageMock(BaseModel):
    """Message mock"""

    content: str


class ChoiceMock(BaseModel):
    """Choice mock"""

    message: MessageMock


class ChatCompletionMock(BaseModel):
    """ChatCompletion mock"""

    id: str
    choices: List[ChoiceMock]


def test_api_ai__unauthentified():
    """Unauthentified users should not be allowed"""

    client = APIClient()
    response = client.post("/api/v1.0/ai/")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication credentials were not provided."
    }


@pytest.mark.parametrize(
    "setting_name, setting_value",
    [
        ("AI_BASE_URL", None),
        ("AI_API_KEY", None),
        ("AI_MODEL", None),
    ],
)
def test_api_ai_setting_missing(setting_name, setting_value):
    """Setting should be set"""

    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    with override_settings(**{setting_name: setting_value}):
        response = client.post("/api/v1.0/ai/")

    assert response.status_code == 400
    assert response.json() == {"error": "AI configuration not set"}


@override_settings(
    AI_BASE_URL="http://example.com", AI_API_KEY="test-key", AI_MODEL="test-model"
)
def test_api_ai__bad_action_config():
    """
    Action config should raised when the action is not correct
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)
    response = client.post(
        "/api/v1.0/ai/",
        {
            "action": "bad_action",
            "text": "Hello world",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid action"}


@override_settings(
    AI_BASE_URL="http://example.com", AI_API_KEY="test-key", AI_MODEL="test-model"
)
def test_api_ai__client_error():
    """
    Fail when the client raises an error
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_create.side_effect = APIException("Mocked client error")

        response = client.post(
            "/api/v1.0/ai/",
            {
                "action": "translate_fr",
                "text": "Hello world",
            },
        )

        assert response.status_code == 500
        assert response.json() == {
            "error": "Error processing AI response: Mocked client error"
        }


@override_settings(
    AI_BASE_URL="http://example.com", AI_API_KEY="test-key", AI_MODEL="test-model"
)
def test_api_ai__client_invalid_response():
    """
    Fail when the client response is invalid
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_create.return_value = ChatCompletionMock(
            id="test-id",
            choices=[
                ChoiceMock(
                    message=MessageMock(
                        content='{"no_answer": "This is an invalid response"}'
                    )
                )
            ],
        )

        response = client.post(
            "/api/v1.0/ai/",
            {
                "action": "translate_fr",
                "text": "Hello world",
            },
        )

        assert response.status_code == 400
        assert response.json() == {"error": ["Invalid response format"]}


@override_settings(
    AI_BASE_URL="http://example.com", AI_API_KEY="test-key", AI_MODEL="test-model"
)
def test_api_ai__success():
    """
    Test the ai request with a success response
    """
    user = factories.UserFactory()

    client = APIClient()
    client.force_login(user)

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_create.return_value = ChatCompletionMock(
            id="test-id",
            choices=[
                ChoiceMock(message=MessageMock(content='{"answer": "Salut le monde"}'))
            ],
        )

        response = client.post(
            "/api/v1.0/ai/",
            {
                "action": "translate_fr",
                "text": "Hello world",
            },
        )

        assert response.status_code == 200
        assert response.json() == {"answer": "Salut le monde"}
