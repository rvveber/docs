"""Util to generate S3 authorization headers for object storage access control"""

import time

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage

import botocore
from rest_framework.throttling import BaseThrottle


def generate_s3_authorization_headers(key):
    """
    Generate authorization headers for an s3 object.
    These headers can be used as an alternative to signed urls with many benefits:
    - the urls of our files never expire and can be stored in our documents' content
    - we don't leak authorized urls that could be shared (file access can only be done
      with cookies)
    - access control is truly realtime
    - the object storage service does not need to be exposed on internet
    """
    url = default_storage.unsigned_connection.meta.client.generate_presigned_url(
        "get_object",
        ExpiresIn=0,
        Params={"Bucket": default_storage.bucket_name, "Key": key},
    )
    request = botocore.awsrequest.AWSRequest(method="get", url=url)

    s3_client = default_storage.connection.meta.client
    # pylint: disable=protected-access
    credentials = s3_client._request_signer._credentials  # noqa: SLF001
    frozen_credentials = credentials.get_frozen_credentials()
    region = s3_client.meta.region_name
    auth = botocore.auth.S3SigV4Auth(frozen_credentials, "s3", region)
    auth.add_auth(request)

    return request


class AIDocumentRateThrottle(BaseThrottle):
    """Throttle for limiting AI requests per document with backoff."""

    def __init__(self, *args, **kwargs):
        """Initialize instance attributes"""
        super().__init__(*args, **kwargs)
        self.rates = settings.AI_DOCUMENT_RATE_THROTTLE_RATES
        self.cache_key = None
        self.recent_requests_minute = 0
        self.recent_requests_hour = 0
        self.recent_requests_day = 0

    def get_cache_key(self, request, view):
        """Include document ID in the cache key"""
        document_id = view.kwargs["pk"]
        return f"document_{document_id}_throttle_ai"

    def allow_request(self, request, view):
        """Check that limits are not exceeded"""
        self.cache_key = self.get_cache_key(request, view)

        now = time.time()
        history = cache.get(self.cache_key, [])
        history = [
            req for req in history if req > now - 86400
        ]  # Keep requests from the last day

        # Calculate recent requests
        self.recent_requests_minute = len([req for req in history if req > now - 60])
        self.recent_requests_hour = len([req for req in history if req > now - 3600])
        self.recent_requests_day = len(history)

        # Check rate limits
        if self.recent_requests_minute >= self.rates["minute"]:
            return False  # Exceeded minute limit
        if self.recent_requests_hour >= self.rates["hour"]:
            return False  # Exceeded hour limit
        if self.recent_requests_day >= self.rates["day"]:
            return False  # Exceeded daily limit

        # Log the request
        history.append(now)
        cache.set(self.cache_key, history, timeout=86400)
        return True

    def wait(self):
        """Implement a backoff strategy by increasing wait time with each throttle hit."""
        if self.recent_requests_day >= self.rates["day"]:
            return 86400  # Throttled by day limit, wait 24 hours
        if self.recent_requests_hour >= self.rates["hour"]:
            return 3600  # Throttled by hour limit, wait 1 hour
        if self.recent_requests_minute >= self.rates["minute"]:
            return 60  # Throttled by minute limit, wait 1 minute

        return None  # No backoff required


class AIUserRateThrottle(BaseThrottle):
    """Throttle that limits requests per user or IP with backoff and rate limits."""

    def __init__(self, *args, **kwargs):
        """Initialize instance attributes"""
        super().__init__(*args, **kwargs)
        self.rates = settings.AI_USER_RATE_THROTTLE_RATES
        self.cache_key = None
        self.recent_requests_minute = 0
        self.recent_requests_hour = 0
        self.recent_requests_day = 0

    # pylint: disable=unused-argument
    def get_cache_key(self, request, view):
        """Generate a cache key based on the user ID or IP for anonymous users."""
        if request.user.is_authenticated:
            return f"user_{request.user.id!s}_throttle_ai"

        # Use IP address for anonymous users
        ip_addr = self.get_ident(request)
        return f"anonymous_{ip_addr:s}_throttle_ai"

    def allow_request(self, request, view):
        """
        Check if the request should be allowed based on the user-specific or IP-specific usage.
        """
        self.cache_key = self.get_cache_key(request, view)
        if not self.cache_key:
            return True  # Allow requests if no cache key (fallback)

        now = time.time()
        history = cache.get(self.cache_key, [])
        # Remove entries older than a day (86400 seconds)
        history = [req for req in history if req > now - 86400]

        # Calculate recent request counts
        self.recent_requests_minute = len([req for req in history if req > now - 60])
        self.recent_requests_hour = len([req for req in history if req > now - 3600])
        self.recent_requests_day = len(history)

        # Check if the user has exceeded the limits
        if self.recent_requests_minute >= self.rates["minute"]:
            return False  # Exceeded minute limit
        if self.recent_requests_hour >= self.rates["hour"]:
            return False  # Exceeded hour limit
        if self.recent_requests_day >= self.rates["day"]:
            return False  # Exceeded daily limit

        # If not throttled, store the request timestamp
        history.append(now)
        cache.set(self.cache_key, history, timeout=86400)
        return True

    def wait(self):
        """Calculate and return the backoff time based on the number of requests made."""
        if self.recent_requests_day >= self.rates["day"]:
            return 86400  # If the day limit is exceeded, wait 24 hours
        if self.recent_requests_hour >= self.rates["hour"]:
            return 3600  # If the hour limit is exceeded, wait 1 hour
        if self.recent_requests_minute >= self.rates["minute"]:
            return 60  # If the minute limit is exceeded, wait 1 minute

        return None  # No backoff required

    def get_ident(self, request):
        """Return the request IP address."""
        # Use REMOTE_ADDR for IP identification, or X-Forwarded-For if behind a proxy
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
