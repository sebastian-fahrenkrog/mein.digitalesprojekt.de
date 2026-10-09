# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - public API routes for project pages.

from django.urls import path

from plane.api.views.page import (
    ProjectPageArchiveAPIEndpoint,
    ProjectPageDetailAPIEndpoint,
    ProjectPageListCreateAPIEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/",
        ProjectPageListCreateAPIEndpoint.as_view(http_method_names=["get", "post"]),
        name="api-project-pages",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/",
        ProjectPageDetailAPIEndpoint.as_view(http_method_names=["get", "put", "patch", "delete"]),
        name="api-project-page-detail",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/archive/",
        ProjectPageArchiveAPIEndpoint.as_view(http_method_names=["post", "delete"]),
        name="api-project-page-archive",
    ),
]
