# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# custom: fork extension - public API for project pages, mirroring the Plane Cloud page API:
# https://developers.plane.so/api-reference/page/overview

import json
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from plane.api.serializers.page import (
    PageAPISerializer,
    PageCreateAPISerializer,
    PageUpdateAPISerializer,
)
from plane.app.permissions import ProjectPagePermission
from plane.app.views.page.base import unarchive_archive_page_and_descendants
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.page_version_task import track_page_version
from plane.db.models import Page, Project, ProjectMember, ProjectPage, UserFavorite, UserRecentVisit
from plane.utils.live_document import LiveServiceError, LiveServiceNotConfigured, sync_page_content

from .base import BaseAPIView

ADMIN_ROLE = 20
GUEST_ROLE = 5
PAGE_LIST_TYPES = {"all", "public", "private", "shared", "archived"}


def get_member_role(slug, project_id, user):
    return (
        ProjectMember.objects.filter(workspace__slug=slug, project_id=project_id, member=user, is_active=True)
        .values_list("role", flat=True)
        .first()
    )


def is_owner_or_admin(page, user, role):
    return page.owned_by_id == user.id or role == ADMIN_ROLE


class ProjectPageQuerysetMixin:
    """Pages linked to the project that the requesting user may see."""

    def get_page_queryset(self, slug, project_id):
        return (
            Page.objects.filter(
                workspace__slug=slug,
                project_pages__project_id=project_id,
                project_pages__deleted_at__isnull=True,
                projects__archived_at__isnull=True,
            )
            .filter(Q(owned_by=self.request.user) | Q(access=Page.PUBLIC_ACCESS))
            .distinct()
        )

    def get_page(self, slug, project_id, page_id):
        return self.get_page_queryset(slug, project_id).filter(pk=page_id).first()


class ProjectPageListCreateAPIEndpoint(ProjectPageQuerysetMixin, BaseAPIView):
    permission_classes = [ProjectPagePermission]

    def get(self, request, slug, project_id):
        """List pages of a project, filtered by `type` and `search`."""
        page_type = request.GET.get("type", "all")
        if page_type not in PAGE_LIST_TYPES:
            return Response({"error": f"type must be one of {sorted(PAGE_LIST_TYPES)}"}, status=400)

        queryset = self.filter_by_type(self.get_page_queryset(slug, project_id), page_type)
        queryset = self.restrict_for_guests(queryset, slug, project_id)
        search = request.GET.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        return self.paginate(
            request=request,
            queryset=queryset.order_by("-created_at"),
            on_results=lambda pages: PageAPISerializer(pages, many=True).data,
            default_per_page=20,
            max_per_page=100,
        )

    def filter_by_type(self, queryset, page_type):
        if page_type == "archived":
            return queryset.filter(archived_at__isnull=False)
        if page_type == "public":
            return queryset.filter(access=Page.PUBLIC_ACCESS, archived_at__isnull=True)
        if page_type == "private":
            return queryset.filter(access=Page.PRIVATE_ACCESS, owned_by=self.request.user, archived_at__isnull=True)
        if page_type == "shared":
            # The community edition has no page sharing, so nothing is shared explicitly.
            return queryset.none()
        return queryset

    def restrict_for_guests(self, queryset, slug, project_id):
        project = Project.objects.get(pk=project_id)
        role = get_member_role(slug, project_id, self.request.user)
        if role == GUEST_ROLE and not project.guest_view_all_features:
            return queryset.filter(owned_by=self.request.user)
        return queryset

    def post(self, request, slug, project_id):
        """Create a page; `description_html` is converted to the editor format on first open."""
        serializer = PageCreateAPISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        parent_id = data.pop("parent_id", None)
        if parent_id and not self.get_page(slug, project_id, parent_id):
            return Response({"parent_id": "Parent page not found in this project."}, status=400)

        project = Project.objects.get(pk=project_id, workspace__slug=slug)
        page = Page.objects.create(
            **data,
            parent_id=parent_id,
            owned_by=request.user,
            workspace_id=project.workspace_id,
        )
        ProjectPage.objects.create(
            workspace_id=project.workspace_id,
            project_id=project_id,
            page_id=page.id,
            created_by_id=page.created_by_id,
            updated_by_id=page.updated_by_id,
        )
        page_transaction.delay(
            new_description_html=page.description_html, old_description_html=None, page_id=str(page.id)
        )
        return Response(PageAPISerializer(page).data, status=status.HTTP_201_CREATED)


class ProjectPageDetailAPIEndpoint(ProjectPageQuerysetMixin, BaseAPIView):
    permission_classes = [ProjectPagePermission]

    def get(self, request, slug, project_id, page_id):
        page = self.get_page(slug, project_id, page_id)
        if not page:
            return Response({"error": "Page not found."}, status=404)
        return Response(PageAPISerializer(page).data)

    def put(self, request, slug, project_id, page_id):
        """Replace title and/or content. Content changes go through the live document."""
        page = self.get_page(slug, project_id, page_id)
        if not page:
            return Response({"error": "Page not found."}, status=404)
        if page.is_locked:
            return Response({"error": "Page is locked."}, status=400)
        if page.archived_at:
            return Response({"error": "Page is archived."}, status=400)

        serializer = PageUpdateAPISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.apply_update(request, page, serializer.validated_data)

    def patch(self, request, slug, project_id, page_id):
        return self.put(request, slug, project_id, page_id)

    def apply_update(self, request, page, data):
        old_html = page.description_html
        existing_instance = json.dumps({"description_html": old_html}, cls=DjangoJSONEncoder)
        try:
            result = sync_page_content(page, name=data.get("name"), description_html=data.get("description_html"))
        except LiveServiceNotConfigured as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except LiveServiceError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if "name" in data:
            page.name = data["name"]
        page.description_binary = result["description_binary"]
        page.description_html = result["description_html"]
        page.description_json = result["description_json"]
        page.save()

        if "description_html" in data:
            page_transaction.delay(
                new_description_html=page.description_html, old_description_html=old_html, page_id=str(page.id)
            )
            track_page_version.delay(page_id=str(page.id), existing_instance=existing_instance, user_id=request.user.id)
        return Response(PageAPISerializer(page).data)

    def delete(self, request, slug, project_id, page_id):
        """Delete an archived page; children are detached, not deleted."""
        page = self.get_page(slug, project_id, page_id)
        if not page:
            return Response({"error": "Page not found."}, status=404)
        if page.archived_at is None:
            return Response({"error": "The page should be archived before deleting."}, status=400)
        if not is_owner_or_admin(page, request.user, get_member_role(slug, project_id, request.user)):
            return Response({"error": "Only admin or owner can delete the page."}, status=403)

        Page.objects.filter(parent_id=page_id, workspace__slug=slug).update(parent=None)
        page.delete()
        UserFavorite.objects.filter(
            project=project_id, workspace__slug=slug, entity_identifier=page_id, entity_type="page"
        ).delete()
        UserRecentVisit.objects.filter(
            project_id=project_id, workspace__slug=slug, entity_identifier=page_id, entity_name="page"
        ).delete(soft=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectPageArchiveAPIEndpoint(ProjectPageQuerysetMixin, BaseAPIView):
    permission_classes = [ProjectPagePermission]

    def post(self, request, slug, project_id, page_id):
        """Archive a page and its subpages."""
        page = self.get_page(slug, project_id, page_id)
        if not page:
            return Response({"error": "Page not found."}, status=404)
        if not is_owner_or_admin(page, request.user, get_member_role(slug, project_id, request.user)):
            return Response({"error": "Only the owner or admin can archive the page."}, status=403)

        UserFavorite.objects.filter(
            entity_type="page", entity_identifier=page_id, project_id=project_id, workspace__slug=slug
        ).delete()
        unarchive_archive_page_and_descendants(page_id, datetime.now())
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, slug, project_id, page_id):
        """Restore an archived page and its subpages."""
        page = self.get_page(slug, project_id, page_id)
        if not page:
            return Response({"error": "Page not found."}, status=404)
        if not is_owner_or_admin(page, request.user, get_member_role(slug, project_id, request.user)):
            return Response({"error": "Only the owner or admin can restore the page."}, status=403)

        # Restoring under an archived parent would break the hierarchy.
        if page.parent_id and page.parent.archived_at:
            page.parent = None
            page.save(update_fields=["parent"])
        unarchive_archive_page_and_descendants(page_id, None)
        return Response(status=status.HTTP_204_NO_CONTENT)
