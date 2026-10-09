/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - time tracking (worklogs) on work items.

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TIssueWorkLog = {
  id: string;
  issue_id: string;
  project_id: string;
  workspace_id: string;
  logged_by: string;
  /** minutes */
  duration: number;
  description: string;
  /** YYYY-MM-DD */
  date: string;
  created_at: string;
  updated_at: string;
};

export type TIssueWorkLogPayload = Pick<TIssueWorkLog, "duration" | "description" | "date" | "logged_by">;

export class IssueWorkLogService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private basePath(workspaceSlug: string, projectId: string, issueId: string) {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`;
  }

  async list(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueWorkLog[]> {
    return this.get(this.basePath(workspaceSlug, projectId, issueId))
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: TIssueWorkLogPayload
  ): Promise<TIssueWorkLog> {
    return this.post(this.basePath(workspaceSlug, projectId, issueId), data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    workLogId: string,
    data: Partial<TIssueWorkLogPayload>
  ): Promise<TIssueWorkLog> {
    return this.patch(`${this.basePath(workspaceSlug, projectId, issueId)}${workLogId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, projectId: string, issueId: string, workLogId: string): Promise<void> {
    return this.delete(`${this.basePath(workspaceSlug, projectId, issueId)}${workLogId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
