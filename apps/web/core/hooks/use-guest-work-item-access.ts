/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - customers are project guests. They may create work items and edit
// the content (title, description, priority, links, attachments) of the ones they created;
// planning properties and time tracking stay with admins and members.

import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// hooks
import { useUser, useUserPermissions } from "@/hooks/store/user";

/** Ids of the current workspace's projects in which the user may create work items (incl. guests). */
export const useWorkItemCreateProjectIds = (workspaceSlug: string | undefined): string[] => {
  const { getProjectRolesByWorkspaceSlug } = useUserPermissions();
  const roles = workspaceSlug ? getProjectRolesByWorkspaceSlug(workspaceSlug) : undefined;
  if (!roles) return [];
  return Object.keys(roles).filter((projectId) => (roles[projectId] ?? 0) >= EUserPermissions.GUEST);
};

/** Role-based access to a work item for the current user. */
export const useWorkItemContentAccess = (
  workspaceSlug: string | undefined,
  projectId: string | undefined,
  createdBy?: string | null
) => {
  const { data: currentUser } = useUser();
  const { allowPermissions } = useUserPermissions();
  const isStaff = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug,
    projectId
  );
  const isGuest =
    !isStaff && allowPermissions([EUserPermissions.GUEST], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId);
  const isCreator = !!createdBy && createdBy === currentUser?.id;
  return {
    isStaff,
    isGuest,
    /** title, description, links and attachments */
    canEditContent: isStaff || (isGuest && isCreator),
  };
};
