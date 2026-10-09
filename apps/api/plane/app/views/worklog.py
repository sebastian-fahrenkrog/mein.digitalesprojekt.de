# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - session-authenticated worklog endpoints for the web app.

from plane.app.permissions import ProjectEntityPermission
from plane.utils.worklog import ProjectWorkLogSummaryMixin, WorkLogDetailMixin, WorkLogListCreateMixin

from .base import BaseAPIView


class IssueWorkLogEndpoint(WorkLogListCreateMixin, BaseAPIView):
    permission_classes = [ProjectEntityPermission]


class IssueWorkLogDetailEndpoint(WorkLogDetailMixin, BaseAPIView):
    permission_classes = [ProjectEntityPermission]


class ProjectWorkLogSummaryEndpoint(ProjectWorkLogSummaryMixin, BaseAPIView):
    permission_classes = [ProjectEntityPermission]
