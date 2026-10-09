/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - "Time tracking" widget in the work item detail and peek view.

import React from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssueServiceType } from "@plane/types";
import { Collapsible, CollapsibleButton } from "@plane/ui";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// services
import type { TIssueWorkLogPayload } from "@/services/issue/issue_worklog.service";
import { IssueWorkLogService } from "@/services/issue/issue_worklog.service";
// local imports
import { WorkLogCollapsibleContent } from "./content";
import { formatMinutes } from "./helper";

const workLogService = new IssueWorkLogService();

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled?: boolean;
  issueServiceType: TIssueServiceType;
};

export const WorkLogCollapsible = observer(function WorkLogCollapsible(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled = false, issueServiceType } = props;
  const { t } = useTranslation();
  // store hooks
  const { openWidgets, toggleOpenWidget, activity } = useIssueDetail(issueServiceType);
  const isOpen = openWidgets.includes("worklog");
  // data
  const { data: workLogs = [], mutate } = useSWR(`ISSUE_WORKLOGS_${issueId}`, () =>
    workLogService.list(workspaceSlug, projectId, issueId)
  );
  const totalMinutes = workLogs.reduce((sum, workLog) => sum + workLog.duration, 0);

  // refresh list and activity feed after every change
  const refresh = async () => {
    await mutate();
    // call on the store object: fetchActivities is a class method and needs its `this`
    void activity.fetchActivities(workspaceSlug, projectId, issueId);
  };
  const handleCreate = async (data: TIssueWorkLogPayload) => {
    await workLogService.create(workspaceSlug, projectId, issueId, data);
    await refresh();
  };
  const handleUpdate = async (workLogId: string, data: TIssueWorkLogPayload) => {
    await workLogService.update(workspaceSlug, projectId, issueId, workLogId, data);
    await refresh();
  };
  const handleDelete = async (workLogId: string) => {
    await workLogService.remove(workspaceSlug, projectId, issueId, workLogId);
    await refresh();
  };

  return (
    <Collapsible
      isOpen={isOpen}
      onToggle={() => toggleOpenWidget("worklog")}
      title={
        <CollapsibleButton
          isOpen={isOpen}
          title={t("worklog.title")}
          indicatorElement={
            <span className="text-13 text-tertiary">
              {t("worklog.total")}: {formatMinutes(totalMinutes)}
            </span>
          }
        />
      }
      buttonClassName="w-full"
    >
      <WorkLogCollapsibleContent
        projectId={projectId}
        workLogs={workLogs}
        disabled={disabled}
        onCreate={handleCreate}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
      />
    </Collapsible>
  );
});
