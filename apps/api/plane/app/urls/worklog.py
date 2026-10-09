# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - web app routes for worklogs.

from django.urls import path

from plane.app.views.worklog import (
    IssueWorkLogDetailEndpoint,
    IssueWorkLogEndpoint,
    ProjectWorkLogSummaryEndpoint,
)

PROJECT = "workspaces/<str:slug>/projects/<uuid:project_id>"

urlpatterns = [
    path(
        f"{PROJECT}/issues/<uuid:issue_id>/worklogs/",
        IssueWorkLogEndpoint.as_view(http_method_names=["get", "post"]),
        name="project-issue-worklogs",
    ),
    path(
        f"{PROJECT}/issues/<uuid:issue_id>/worklogs/<uuid:pk>/",
        IssueWorkLogDetailEndpoint.as_view(http_method_names=["patch", "delete"]),
        name="project-issue-worklog-detail",
    ),
    path(
        f"{PROJECT}/total-worklogs/",
        ProjectWorkLogSummaryEndpoint.as_view(http_method_names=["get"]),
        name="project-total-worklogs",
    ),
]
