# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - shared worklog logic for the public API and the web app endpoints.

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from plane.api.serializers.worklog import WorkLogSerializer
from plane.db.models import Issue, IssueActivity, IssueWorkLog, ProjectMember

ACTIVITY_FIELD = "worklog"
# Time tracking is internal: only project admins (20) and members (15) see it, never guests (5),
# who are the role used for customers.
STAFF_ROLES = (20, 15)


def staff_project_ids(user):
    """Projects in which `user` counts as staff (admin or member)."""
    return ProjectMember.objects.filter(member=user, is_active=True, role__in=STAFF_ROLES).values("project_id")


def hide_worklog_activity_for_guests(queryset, user):
    """Drop worklog activity entries from projects where `user` is not staff."""
    return queryset.filter(~Q(field=ACTIVITY_FIELD) | Q(project_id__in=staff_project_ids(user)))


class ProjectStaffPermission(BasePermission):
    """Allow any method only for active admins and members of the project in the URL."""

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        return ProjectMember.objects.filter(
            workspace__slug=view.kwargs.get("slug"),
            project_id=view.kwargs.get("project_id"),
            member=request.user,
            is_active=True,
            role__in=STAFF_ROLES,
        ).exists()


def format_minutes(minutes):
    """Human readable duration such as '1h 30m' for activity entries."""
    hours, rest = divmod(int(minutes), 60)
    if hours and rest:
        return f"{hours}h {rest}m"
    return f"{hours}h" if hours else f"{rest}m"


def record_worklog_activity(worklog, verb, actor_id, old_duration=None):
    """Add an entry to the work item's activity feed (rendered by the web app for field 'worklog')."""
    IssueActivity.objects.create(
        issue_id=worklog.issue_id,
        project_id=worklog.project_id,
        workspace_id=worklog.workspace_id,
        actor_id=actor_id,
        verb=verb,
        field=ACTIVITY_FIELD,
        old_value=str(old_duration) if old_duration is not None else None,
        new_value=str(worklog.duration) if verb != "deleted" else None,
        new_identifier=worklog.id if verb != "deleted" else None,
        old_identifier=worklog.id if verb == "deleted" else None,
        comment=f"{verb} worklog {format_minutes(worklog.duration)}",
        epoch=int(timezone.now().timestamp()),
    )


class WorkLogListCreateMixin:
    """GET: all worklogs of a work item as a plain list. POST: log time for the requesting user."""

    def get_issue(self, slug, project_id, issue_id):
        return get_object_or_404(Issue, pk=issue_id, project_id=project_id, workspace__slug=slug)

    def get(self, request, slug, project_id, issue_id):
        self.get_issue(slug, project_id, issue_id)
        worklogs = IssueWorkLog.objects.filter(issue_id=issue_id, project_id=project_id, workspace__slug=slug)
        return Response(WorkLogSerializer(worklogs, many=True).data)

    def post(self, request, slug, project_id, issue_id):
        issue = self.get_issue(slug, project_id, issue_id)
        serializer = WorkLogSerializer(data=request.data, context={"project_id": project_id})
        serializer.is_valid(raise_exception=True)
        if "logged_by_id" not in serializer.validated_data:
            serializer.validated_data["logged_by_id"] = request.user.id
        worklog = serializer.save(issue=issue, project_id=project_id)
        record_worklog_activity(worklog, "created", request.user.id)
        return Response(WorkLogSerializer(worklog).data, status=status.HTTP_201_CREATED)


class WorkLogDetailMixin:
    """PATCH/DELETE a worklog; any project member with write access may change any entry."""

    def get_worklog(self, slug, project_id, issue_id, pk):
        return get_object_or_404(IssueWorkLog, pk=pk, issue_id=issue_id, project_id=project_id, workspace__slug=slug)

    def patch(self, request, slug, project_id, issue_id, pk):
        worklog = self.get_worklog(slug, project_id, issue_id, pk)
        old_duration = worklog.duration
        serializer = WorkLogSerializer(worklog, data=request.data, partial=True, context={"project_id": project_id})
        serializer.is_valid(raise_exception=True)
        worklog = serializer.save()
        record_worklog_activity(worklog, "updated", request.user.id, old_duration=old_duration)
        return Response(WorkLogSerializer(worklog).data)

    def delete(self, request, slug, project_id, issue_id, pk):
        worklog = self.get_worklog(slug, project_id, issue_id, pk)
        record_worklog_activity(worklog, "deleted", request.user.id, old_duration=worklog.duration)
        worklog.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectWorkLogSummaryMixin:
    """Total logged minutes per work item of a project: [{issue_id, duration}]."""

    def get(self, request, slug, project_id):
        totals = (
            IssueWorkLog.objects.filter(project_id=project_id, workspace__slug=slug)
            .values("issue_id")
            .annotate(duration=Sum("duration"))
            .order_by("issue_id")
        )
        return Response([{"issue_id": str(row["issue_id"]), "duration": row["duration"]} for row in totals])
