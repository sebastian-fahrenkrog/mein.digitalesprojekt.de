/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - list of time entries with inline create/edit/delete.

import React, { useState } from "react";
import { observer } from "mobx-react";
import { Pencil, Trash2 } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { renderFormattedDate } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import type { TIssueWorkLog, TIssueWorkLogPayload } from "@/services/issue/issue_worklog.service";
// local imports
import { WorkLogForm } from "./form";
import { formatMinutes } from "./helper";

type Props = {
  projectId: string;
  workLogs: TIssueWorkLog[];
  disabled: boolean;
  onCreate: (data: TIssueWorkLogPayload) => Promise<void>;
  onUpdate: (workLogId: string, data: TIssueWorkLogPayload) => Promise<void>;
  onDelete: (workLogId: string) => Promise<void>;
};

export const WorkLogCollapsibleContent = observer(function WorkLogCollapsibleContent(props: Props) {
  const { projectId, workLogs, disabled, onCreate, onUpdate, onDelete } = props;
  const { t } = useTranslation();
  const [editingId, setEditingId] = useState<string | null>(null);
  // store hooks
  const { getUserDetails } = useMember();

  const withToast = async (action: () => Promise<void>, successKey: string) => {
    try {
      await action();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t(successKey) });
    } catch (error) {
      const message = (error as { error?: string } | undefined)?.error;
      setToast({ type: TOAST_TYPE.ERROR, title: t("worklog.toasts.error"), message });
      throw error;
    }
  };

  return (
    <div className="flex flex-col gap-2 py-2">
      {!disabled && (
        <WorkLogForm
          projectId={projectId}
          onSubmit={(data) => withToast(() => onCreate(data), "worklog.toasts.created")}
        />
      )}
      {workLogs.length === 0 && <p className="text-13 text-tertiary">{t("worklog.empty")}</p>}
      {workLogs.map((workLog) => {
        // every project member who may edit the work item may change any entry
        const canModify = !disabled;
        if (editingId === workLog.id)
          return (
            <WorkLogForm
              key={workLog.id}
              projectId={projectId}
              initialValue={workLog}
              onCancel={() => setEditingId(null)}
              onSubmit={async (data) => {
                await withToast(() => onUpdate(workLog.id, data), "worklog.toasts.updated");
                setEditingId(null);
              }}
            />
          );
        return (
          <div key={workLog.id} className="flex items-center gap-3 rounded-md px-2 py-1.5 text-13 hover:bg-layer-1">
            <span className="w-16 shrink-0 font-medium text-primary">{formatMinutes(workLog.duration)}</span>
            <span className="w-24 shrink-0 text-secondary">{renderFormattedDate(workLog.date)}</span>
            <span className="w-32 shrink-0 truncate text-secondary">
              {getUserDetails(workLog.logged_by)?.display_name ?? ""}
            </span>
            <span className="flex-1 truncate text-primary">{workLog.description}</span>
            {canModify && (
              <span className="flex shrink-0 items-center gap-1 text-tertiary">
                <button
                  type="button"
                  aria-label={t("worklog.edit")}
                  className="rounded p-1 text-secondary hover:text-primary"
                  onClick={() => setEditingId(workLog.id)}
                >
                  <Pencil className="size-3.5" />
                </button>
                <button
                  type="button"
                  aria-label={t("worklog.delete")}
                  className="rounded p-1 text-secondary hover:text-danger-primary"
                  onClick={() => void withToast(() => onDelete(workLog.id), "worklog.toasts.deleted")}
                >
                  <Trash2 className="size-3.5" />
                </button>
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
});
