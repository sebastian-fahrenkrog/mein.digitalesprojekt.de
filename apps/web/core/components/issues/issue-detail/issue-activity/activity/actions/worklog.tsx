/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - activity entry for time tracking (field "worklog").

import { observer } from "mobx-react";
import { Clock } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { formatMinutes } from "@/components/issues/issue-detail-widgets/worklog/helper";
import { IssueActivityBlockComponent } from "./";

type TIssueWorkLogActivity = { activityId: string; ends: "top" | "bottom" | undefined };

const toDuration = (value: string | null | undefined) => formatMinutes(Number(value ?? 0));

export const IssueWorkLogActivity = observer(function IssueWorkLogActivity(props: TIssueWorkLogActivity) {
  const { activityId, ends } = props;
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);
  if (!activity) return <></>;

  let text: string;
  if (activity.verb === "created") text = t("worklog.activity.created", { duration: toDuration(activity.new_value) });
  else if (activity.verb === "updated")
    text = t("worklog.activity.updated", {
      old: toDuration(activity.old_value),
      new: toDuration(activity.new_value),
    });
  else text = t("worklog.activity.deleted", { duration: toDuration(activity.old_value) });

  return (
    <IssueActivityBlockComponent
      icon={<Clock size={14} className="text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      <span>{text}.</span>
    </IssueActivityBlockComponent>
  );
});
