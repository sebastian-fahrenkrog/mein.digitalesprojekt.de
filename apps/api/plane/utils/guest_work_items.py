# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - customers are project guests; they may create work items and edit
# the content of their own ones, while planning fields stay with the team.

from rest_framework.permissions import SAFE_METHODS, BasePermission

from plane.db.models import Issue, ProjectMember

GUEST_ROLE = 5
STAFF_ROLES = (20, 15)

# Fields a guest may set when creating or updating their own work item.
GUEST_EDITABLE_ISSUE_FIELDS = {
    "name",
    "description_html",
    "description_json",
    "description_binary",
    "priority",
}


def get_project_role(slug, project_id, user):
    return (
        ProjectMember.objects.filter(workspace__slug=slug, project_id=project_id, member=user, is_active=True)
        .values_list("role", flat=True)
        .first()
    )


def restrict_guest_issue_payload(request, slug, project_id):
    """
    For project guests, drop every field except the content fields from the request body.
    State, assignees, labels, cycles, dates etc. fall back to the project defaults.
    """
    if get_project_role(slug, project_id, request.user) != GUEST_ROLE:
        return
    if not isinstance(request.data, dict):
        return
    allowed = {key: value for key, value in request.data.items() if key in GUEST_EDITABLE_ISSUE_FIELDS}
    # DRF caches the parsed body here; replacing it changes what request.data returns.
    request._full_data = allowed


class ProjectEntityOrGuestCreatorPermission(BasePermission):
    """
    Like ProjectEntityPermission, plus: a project guest may write sub-resources (e.g. links)
    of work items they created themselves.
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        slug = view.kwargs.get("slug")
        project_id = view.kwargs.get("project_id")
        role = get_project_role(slug, project_id, request.user)
        if role is None:
            return False
        if request.method in SAFE_METHODS or role in STAFF_ROLES:
            return True
        return (
            role == GUEST_ROLE
            and Issue.objects.filter(
                pk=view.kwargs.get("issue_id"), project_id=project_id, created_by=request.user
            ).exists()
        )
