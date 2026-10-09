# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - public API (X-API-Key) for worklogs, mirroring the Plane Cloud worklog API:
# https://developers.plane.so/api-reference/worklogs/overview

from plane.utils.worklog import (
    ProjectStaffPermission,
    ProjectWorkLogSummaryMixin,
    WorkLogDetailMixin,
    WorkLogListCreateMixin,
)

from .base import BaseAPIView


class WorkLogListCreateAPIEndpoint(WorkLogListCreateMixin, BaseAPIView):
    permission_classes = [ProjectStaffPermission]


class WorkLogDetailAPIEndpoint(WorkLogDetailMixin, BaseAPIView):
    permission_classes = [ProjectStaffPermission]


class ProjectWorkLogSummaryAPIEndpoint(ProjectWorkLogSummaryMixin, BaseAPIView):
    permission_classes = [ProjectStaffPermission]
