# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - public API for project pages (mirrors the Plane Cloud page API).

from rest_framework import serializers

from .base import BaseSerializer
from plane.db.models import Page
from plane.utils.content_validator import validate_html_content


def sanitize_page_html(html):
    """Sanitize page HTML with the shared nh3 validator, raising a validation error if rejected."""
    is_valid, error_msg, sanitized_html = validate_html_content(html)
    if not is_valid:
        raise serializers.ValidationError({"description_html": error_msg or "html content is not valid"})
    return sanitized_html if sanitized_html is not None else html


class PageAPISerializer(BaseSerializer):
    """Read representation of a project page."""

    parent_id = serializers.UUIDField(read_only=True)
    owned_by_id = serializers.UUIDField(read_only=True)
    workspace_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "description_html",
            "access",
            "color",
            "is_locked",
            "archived_at",
            "parent_id",
            "owned_by_id",
            "workspace_id",
            "view_props",
            "logo_props",
            "sort_order",
            "external_id",
            "external_source",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = fields


class PageCreateAPISerializer(BaseSerializer):
    """Validates the body of a page create request."""

    parent_id = serializers.UUIDField(required=False, allow_null=True)
    description_html = serializers.CharField(required=False, allow_blank=True, default="<p></p>")

    class Meta:
        model = Page
        fields = [
            "name",
            "description_html",
            "access",
            "color",
            "is_locked",
            "view_props",
            "logo_props",
            "external_id",
            "external_source",
            "parent_id",
        ]
        extra_kwargs = {"name": {"required": True, "allow_blank": False}}

    def validate_description_html(self, value):
        return sanitize_page_html(value or "<p></p>")


class PageUpdateAPISerializer(serializers.Serializer):
    """Validates the body of a page update request: name and/or description_html."""

    name = serializers.CharField(required=False, allow_blank=False, max_length=255)
    description_html = serializers.CharField(required=False, allow_blank=True)

    def validate_description_html(self, value):
        return sanitize_page_html(value or "<p></p>")

    def validate(self, data):
        if "name" not in data and "description_html" not in data:
            raise serializers.ValidationError("At least one of name or description_html is required.")
        return data
