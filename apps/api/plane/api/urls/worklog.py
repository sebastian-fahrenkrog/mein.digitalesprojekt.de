# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - public API routes for worklogs. Served under both the current
# `work-items` path and the legacy `issues` path that existing clients still use.

from django.urls import path

from plane.api.views.worklog import (
    ProjectWorkLogSummaryAPIEndpoint,
    WorkLogDetailAPIEndpoint,
    WorkLogListCreateAPIEndpoint,
)

PROJECT = "workspaces/<str:slug>/projects/<uuid:project_id>"

urlpatterns = [
    path(
        f"{PROJECT}/total-worklogs/",
        ProjectWorkLogSummaryAPIEndpoint.as_view(http_method_names=["get"]),
        name="api-project-total-worklogs",
    ),
]

for prefix in ("work-items", "issues"):
    urlpatterns += [
        path(
            f"{PROJECT}/{prefix}/<uuid:issue_id>/worklogs/",
            WorkLogListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
            name=f"api-{prefix}-worklogs",
        ),
        path(
            f"{PROJECT}/{prefix}/<uuid:issue_id>/worklogs/<uuid:pk>/",
            WorkLogDetailAPIEndpoint.as_view(http_method_names=["patch", "delete"]),
            name=f"api-{prefix}-worklog-detail",
        ),
    ]
