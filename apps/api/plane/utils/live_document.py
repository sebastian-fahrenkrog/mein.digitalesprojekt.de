# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - lets the API change page content through the live (collaboration) server.

import base64
import logging
import os

import requests
from django.conf import settings

from plane.utils.url import normalize_url_path

logger = logging.getLogger("plane.api")

LIVE_REQUEST_TIMEOUT_SECONDS = 30


class LiveServiceNotConfigured(Exception):
    """The live server URL or secret is missing."""


class LiveServiceError(Exception):
    """The live server could not apply the change."""


def get_live_internal_url():
    """URL the API uses to reach the live server; falls back to the public LIVE_URL."""
    return os.environ.get("LIVE_INTERNAL_URL") or settings.LIVE_URL


def build_content_sync_payload(page, name=None, description_html=None):
    payload = {
        "page_id": str(page.id),
        "description_binary": (
            base64.b64encode(bytes(page.description_binary)).decode() if page.description_binary else None
        ),
        "current_description_html": page.description_html,
        "current_name": page.name,
    }
    if name is not None:
        payload["name"] = name
    if description_html is not None:
        payload["description_html"] = description_html
    return payload


def sync_page_content(page, name=None, description_html=None):
    """
    Apply a new title and/or HTML body to a page via the live server.

    The live server edits the collaborative (Yjs) document in place when the page is open,
    so connected editors stay consistent. Returns the resulting
    description_binary (bytes), description_html and description_json.
    """
    live_url = get_live_internal_url()
    secret = os.environ.get("LIVE_SERVER_SECRET_KEY")
    if not live_url or not secret:
        raise LiveServiceNotConfigured("LIVE_INTERNAL_URL/LIVE_BASE_URL or LIVE_SERVER_SECRET_KEY is not set")

    url = normalize_url_path(f"{live_url}/content-sync/")
    try:
        response = requests.post(
            url,
            json=build_content_sync_payload(page, name=name, description_html=description_html),
            headers={"live-server-secret-key": secret},
            timeout=LIVE_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise LiveServiceError(f"live server not reachable: {exc}") from exc

    if response.status_code != 200:
        logger.error("Live content sync failed", extra={"status": response.status_code, "body": response.text[:500]})
        raise LiveServiceError(f"live server returned {response.status_code}")

    data = response.json()
    return {
        "description_binary": base64.b64decode(data["description_binary"]),
        "description_html": data["description_html"],
        "description_json": data["description_json"],
    }
