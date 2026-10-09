# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - contract tests for the public project pages API.

import pytest
from rest_framework import status

from plane.db.models import Page, Project, ProjectMember, ProjectPage
from plane.utils.live_document import LiveServiceError, LiveServiceNotConfigured


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Wiki Project", identifier="WK", workspace=workspace)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def pages_url(workspace, project):
    return f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/pages/"


@pytest.fixture
def page(db, workspace, project, create_user):
    page = Page.objects.create(name="Handbook", owned_by=create_user, workspace=workspace)
    ProjectPage.objects.create(workspace=workspace, project=project, page=page)
    return page


@pytest.fixture
def fake_live(monkeypatch):
    """Replace the live server call; records calls and returns the requested HTML."""
    calls = []

    def fake_sync(page, name=None, description_html=None):
        calls.append({"name": name, "description_html": description_html})
        return {
            "description_binary": b"\x00",
            "description_html": description_html if description_html is not None else page.description_html,
            "description_json": {"type": "doc"},
        }

    monkeypatch.setattr("plane.api.views.page.sync_page_content", fake_sync)
    return calls


@pytest.mark.contract
class TestPageAPI:
    @pytest.mark.django_db
    def test_create_sanitizes_html_and_links_project(self, api_key_client, project, pages_url):
        response = api_key_client.post(
            pages_url,
            {"name": "Onboarding", "description_html": "<h2>Hi</h2><script>alert(1)</script>"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "<script>" not in response.data["description_html"]
        assert ProjectPage.objects.filter(project=project, page_id=response.data["id"]).exists()

    @pytest.mark.django_db
    def test_create_child_page(self, api_key_client, pages_url, page):
        response = api_key_client.post(pages_url, {"name": "Child", "parent_id": str(page.id)}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["parent_id"] == str(page.id)

    @pytest.mark.django_db
    def test_list_filters_by_search_and_type(self, api_key_client, pages_url, page):
        found = api_key_client.get(pages_url, {"search": "hand"})
        archived = api_key_client.get(pages_url, {"type": "archived"})
        invalid = api_key_client.get(pages_url, {"type": "nope"})

        assert [str(p["id"]) for p in found.data["results"]] == [str(page.id)]
        assert archived.data["results"] == []
        assert invalid.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_update_goes_through_live_document(self, api_key_client, pages_url, page, fake_live):
        response = api_key_client.put(
            f"{pages_url}{page.id}/", {"name": "Handbook v2", "description_html": "<p>new</p>"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert fake_live == [{"name": "Handbook v2", "description_html": "<p>new</p>"}]
        page.refresh_from_db()
        assert page.name == "Handbook v2"
        assert page.description_html == "<p>new</p>"

    @pytest.mark.django_db
    def test_update_requires_a_field(self, api_key_client, pages_url, page, fake_live):
        response = api_key_client.put(f"{pages_url}{page.id}/", {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert fake_live == []

    @pytest.mark.django_db
    def test_update_locked_page_is_rejected(self, api_key_client, pages_url, page, fake_live):
        Page.objects.filter(pk=page.pk).update(is_locked=True)

        response = api_key_client.put(f"{pages_url}{page.id}/", {"name": "x"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "error, expected",
        [(LiveServiceNotConfigured("off"), 503), (LiveServiceError("down"), 502)],
    )
    def test_update_maps_live_errors(self, api_key_client, pages_url, page, monkeypatch, error, expected):
        def failing_sync(*args, **kwargs):
            raise error

        monkeypatch.setattr("plane.api.views.page.sync_page_content", failing_sync)

        response = api_key_client.put(f"{pages_url}{page.id}/", {"description_html": "<p>x</p>"}, format="json")

        assert response.status_code == expected

    @pytest.mark.django_db
    def test_archive_restore_delete_flow(self, api_key_client, pages_url, page):
        detail = f"{pages_url}{page.id}/"

        assert api_key_client.delete(detail).status_code == status.HTTP_400_BAD_REQUEST
        assert api_key_client.post(f"{detail}archive/").status_code == status.HTTP_204_NO_CONTENT
        assert api_key_client.delete(f"{detail}archive/").status_code == status.HTTP_204_NO_CONTENT
        page.refresh_from_db()
        assert page.archived_at is None

        api_key_client.post(f"{detail}archive/")
        assert api_key_client.delete(detail).status_code == status.HTTP_204_NO_CONTENT
        assert not Page.objects.filter(pk=page.pk).exists()
