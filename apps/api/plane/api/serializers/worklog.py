# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - worklog (time tracking) serializer, field names as in the Plane Cloud API.

from rest_framework import serializers

from plane.db.models import IssueWorkLog, ProjectMember

# 24 hours per entry is a sanity limit, not a business rule
MAX_DURATION_MINUTES = 24 * 60


class WorkLogSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(read_only=True)
    workspace_id = serializers.UUIDField(read_only=True)
    issue_id = serializers.UUIDField(read_only=True)
    # writable: time can be logged for any active project member; defaults to the requesting user
    logged_by = serializers.UUIDField(source="logged_by_id", required=False)
    duration = serializers.IntegerField(min_value=1, max_value=MAX_DURATION_MINUTES)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    date = serializers.DateField(required=False)

    class Meta:
        model = IssueWorkLog
        fields = [
            "id",
            "created_at",
            "updated_at",
            "deleted_at",
            "description",
            "duration",
            "date",
            "created_by",
            "updated_by",
            "project_id",
            "workspace_id",
            "issue_id",
            "logged_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at", "created_by", "updated_by"]

    def validate_logged_by(self, value):
        project_id = self.context.get("project_id")
        is_member = ProjectMember.objects.filter(
            project_id=project_id, member_id=value, is_active=True, member__is_bot=False
        ).exists()
        if not is_member:
            raise serializers.ValidationError("User is not an active member of this project.")
        return value
