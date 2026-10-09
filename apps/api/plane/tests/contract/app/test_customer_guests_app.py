# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - customers are project guests: they may create work items and edit the
# content of their own ones, but never see time tracking.

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueActivity,
    IssueLink,
    IssueWorkLog,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

BASE = "/api/workspaces/{slug}/projects/{project_id}"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Customer Project", identifier="CP", workspace=workspace)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    State.objects.create(name="Backlog", project=project, workspace=workspace, group="backlog", default=True)
    return project


@pytest.fixture
def guest(db, workspace, project):
    unique_id = uuid4().hex[:8]
    user = User.objects.create(email=f"customer-{unique_id}@example.com", username=f"customer_{unique_id}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=5)
    ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=5)
    return user


@pytest.fixture
def guest_client(guest):
    client = APIClient()
    client.force_authenticate(user=guest)
    return client


@pytest.fixture
def staff_client(create_user):
    client = APIClient()
    client.force_authenticate(user=create_user)
    return client


def make_issue(project, author, name="Ticket"):
    issue = Issue(name=name, project=project, workspace=project.workspace)
    issue.save(created_by_id=author.id)
    return issue


def base_url(workspace, project):
    return BASE.format(slug=workspace.slug, project_id=project.id)


@pytest.mark.contract
class TestGuestTimeTrackingVisibility:
    @pytest.mark.django_db
    def test_guest_cannot_read_or_write_worklogs(self, guest_client, workspace, project, guest):
        issue = make_issue(project, guest)
        url = f"{base_url(workspace, project)}/issues/{issue.id}/worklogs/"

        assert guest_client.get(url).status_code == status.HTTP_403_FORBIDDEN
        assert guest_client.post(url, {"duration": 30}, format="json").status_code == status.HTTP_403_FORBIDDEN
        total = guest_client.get(f"{base_url(workspace, project)}/total-worklogs/")
        assert total.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_worklog_activity_hidden_from_guest_only(self, guest_client, staff_client, workspace, project, guest):
        issue = make_issue(project, guest)
        url = f"{base_url(workspace, project)}/issues/{issue.id}/worklogs/"
        assert staff_client.post(url, {"duration": 45}, format="json").status_code == status.HTTP_201_CREATED
        assert IssueActivity.objects.filter(issue=issue, field="worklog").exists()

        # the web app always requests the property feed separately from comments
        history = f"{base_url(workspace, project)}/issues/{issue.id}/history/?activity_type=issue-property"
        staff_fields = [a["field"] for a in staff_client.get(history).data]
        guest_fields = [a["field"] for a in guest_client.get(history).data]

        assert "worklog" in staff_fields
        assert "worklog" not in guest_fields


@pytest.mark.contract
class TestGuestWorkItems:
    @pytest.mark.django_db
    def test_guest_creates_work_item_with_content_fields_only(
        self, guest_client, create_user, workspace, project, guest
    ):
        response = guest_client.post(
            f"{base_url(workspace, project)}/issues/",
            {
                "name": "Bitte Logo austauschen",
                "description_html": "<p>Details</p>",
                "priority": "high",
                "assignee_ids": [str(create_user.id)],
                "start_date": "2026-10-01",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        issue = Issue.objects.get(pk=response.data["id"])
        assert issue.name == "Bitte Logo austauschen"
        assert issue.priority == "high"
        assert issue.created_by_id == guest.id
        assert issue.start_date is None
        assert not issue.assignees.exists()
        assert issue.state.default is True

    @pytest.mark.django_db
    def test_guest_edits_content_of_own_work_item_but_not_planning(self, guest_client, workspace, project, guest):
        issue = make_issue(project, guest)
        other_state = State.objects.create(name="Done", project=project, workspace=workspace, group="completed")

        response = guest_client.patch(
            f"{base_url(workspace, project)}/issues/{issue.id}/",
            {"name": "Neuer Titel", "priority": "urgent", "state_id": str(other_state.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        issue.refresh_from_db()
        assert issue.name == "Neuer Titel"
        assert issue.priority == "urgent"
        assert issue.state_id != other_state.id

    @pytest.mark.django_db
    def test_guest_cannot_edit_foreign_work_item(self, guest_client, create_user, workspace, project):
        issue = make_issue(project, create_user)

        response = guest_client.patch(
            f"{base_url(workspace, project)}/issues/{issue.id}/", {"name": "Hijack"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_guest_links_only_on_own_work_items(self, guest_client, create_user, workspace, project, guest):
        own = make_issue(project, guest, "own")
        foreign = make_issue(project, create_user, "foreign")
        link = {"url": "https://example.com", "title": "Beispiel"}

        own_response = guest_client.post(
            f"{base_url(workspace, project)}/issues/{own.id}/issue-links/", link, format="json"
        )
        foreign_response = guest_client.post(
            f"{base_url(workspace, project)}/issues/{foreign.id}/issue-links/", link, format="json"
        )

        assert own_response.status_code == status.HTTP_201_CREATED
        assert foreign_response.status_code == status.HTTP_403_FORBIDDEN
        assert IssueLink.objects.filter(issue=own).count() == 1
        assert IssueWorkLog.objects.count() == 0
