# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - contract tests for the worklog (time tracking) API.

import pytest
from rest_framework import status

from plane.db.models import (
    APIToken,
    Issue,
    IssueActivity,
    IssueWorkLog,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Worklog Project", identifier="WL", workspace=workspace)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def issue(db, workspace, project, create_user):
    state = State.objects.create(name="Todo", project=project, workspace=workspace, group="backlog", default=True)
    return Issue.objects.create(name="Track me", workspace=workspace, project=project, state=state)


@pytest.fixture
def member_client(db, workspace, project, api_client):
    """API client for a second, non-admin project member."""
    member = User.objects.create(email="member@plane.so", username="member", first_name="Member")
    WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
    ProjectMember.objects.create(project=project, member=member, role=15, is_active=True)
    token = APIToken.objects.create(user=member, label="member", token="member-api-token-12345")
    api_client.credentials(HTTP_X_API_KEY=token.token)
    return api_client


def worklogs_url(workspace, project, issue, prefix="work-items"):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/{prefix}/{issue.id}/worklogs/"


@pytest.mark.contract
class TestWorkLogAPI:
    @pytest.mark.django_db
    @pytest.mark.parametrize("prefix", ["work-items", "issues"])
    def test_create_on_both_paths(self, api_key_client, create_user, workspace, project, issue, prefix):
        response = api_key_client.post(
            worklogs_url(workspace, project, issue, prefix),
            {"duration": 90, "description": "Concept", "date": "2026-10-01"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["duration"] == 90
        assert response.data["date"] == "2026-10-01"
        assert response.data["issue_id"] == str(issue.id)
        assert response.data["logged_by"] == str(create_user.id)
        assert IssueWorkLog.objects.filter(issue=issue).count() == 1

    @pytest.mark.django_db
    def test_date_defaults_to_today(self, api_key_client, workspace, project, issue):
        response = api_key_client.post(worklogs_url(workspace, project, issue), {"duration": 30}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["date"] is not None

    @pytest.mark.django_db
    @pytest.mark.parametrize("payload", [{"duration": 0}, {"description": "no duration"}, {"duration": 24 * 60 + 1}])
    def test_rejects_invalid_duration(self, api_key_client, workspace, project, issue, payload):
        response = api_key_client.post(worklogs_url(workspace, project, issue), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert IssueWorkLog.objects.count() == 0

    @pytest.mark.django_db
    def test_list_update_delete_and_activity(self, api_key_client, workspace, project, issue):
        url = worklogs_url(workspace, project, issue)
        worklog_id = api_key_client.post(url, {"duration": 60}, format="json").data["id"]

        listed = api_key_client.get(url)
        assert listed.status_code == status.HTTP_200_OK
        assert [w["id"] for w in listed.data] == [worklog_id]

        updated = api_key_client.patch(f"{url}{worklog_id}/", {"duration": 120}, format="json")
        assert updated.status_code == status.HTTP_200_OK
        assert updated.data["duration"] == 120

        deleted = api_key_client.delete(f"{url}{worklog_id}/")
        assert deleted.status_code == status.HTTP_204_NO_CONTENT
        assert IssueWorkLog.objects.count() == 0

        activities = IssueActivity.objects.filter(issue=issue, field="worklog").order_by("created_at")
        verbs = list(activities.values_list("verb", flat=True))
        assert verbs == ["created", "updated", "deleted"]

    @pytest.mark.django_db
    def test_total_worklogs_per_issue(self, api_key_client, workspace, project, issue):
        url = worklogs_url(workspace, project, issue)
        api_key_client.post(url, {"duration": 45}, format="json")
        api_key_client.post(url, {"duration": 15}, format="json")

        response = api_key_client.get(f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/total-worklogs/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [{"issue_id": str(issue.id), "duration": 60}]

    @pytest.mark.django_db
    def test_member_can_log_and_reassign_for_other_members(self, member_client, create_user, workspace, project, issue):
        url = worklogs_url(workspace, project, issue)

        created = member_client.post(url, {"duration": 30, "logged_by": str(create_user.id)}, format="json")
        assert created.status_code == status.HTTP_201_CREATED
        assert created.data["logged_by"] == str(create_user.id)

        own = member_client.post(url, {"duration": 10}, format="json")
        member_id = own.data["logged_by"]
        assert member_id != str(create_user.id)

        reassigned = member_client.patch(f"{url}{created.data['id']}/", {"logged_by": member_id}, format="json")
        assert reassigned.status_code == status.HTTP_200_OK
        assert reassigned.data["logged_by"] == member_id

    @pytest.mark.django_db
    def test_logged_by_must_be_project_member(self, api_key_client, workspace, project, issue):
        outsider = User.objects.create(email="outsider@plane.so", username="outsider")

        response = api_key_client.post(
            worklogs_url(workspace, project, issue), {"duration": 30, "logged_by": str(outsider.id)}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "logged_by" in response.data
        assert IssueWorkLog.objects.count() == 0

    @pytest.mark.django_db
    def test_unknown_issue_returns_404(self, api_key_client, workspace, project):
        unknown_issue = "00000000-0000-0000-0000-000000000000"
        url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{unknown_issue}/worklogs/"

        assert api_key_client.get(url).status_code == status.HTTP_404_NOT_FOUND
