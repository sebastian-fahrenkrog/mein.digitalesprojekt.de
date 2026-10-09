# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - time tracking on work items (mirrors the Plane Cloud worklog object).

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .project import ProjectBaseModel


def today():
    return timezone.localdate()


class IssueWorkLog(ProjectBaseModel):
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="worklogs")
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="worklogs")
    # time spent in minutes, as in the official API
    duration = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    description = models.TextField(blank=True, default="")
    # fork extension: the day the work was done (the official API only has created_at)
    date = models.DateField(default=today, db_index=True)

    class Meta:
        verbose_name = "Issue Work Log"
        verbose_name_plural = "Issue Work Logs"
        db_table = "issue_worklogs"
        ordering = ("-date", "-created_at")

    def __str__(self):
        return f"{self.issue_id} {self.duration}m"
