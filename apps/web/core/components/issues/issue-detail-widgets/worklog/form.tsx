/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - inline form to log or edit time on a work item.

import React, { useState } from "react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Input } from "@plane/ui";
import { renderFormattedPayloadDate } from "@plane/utils";
// components
import { DateDropdown } from "@/components/dropdowns/date";
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
// hooks
import { useUser } from "@/hooks/store/user";
// services
import type { TIssueWorkLog, TIssueWorkLogPayload } from "@/services/issue/issue_worklog.service";
// local imports
import { minutesToInput, parseDurationToMinutes } from "./helper";

type Props = {
  projectId: string;
  initialValue?: TIssueWorkLog;
  onSubmit: (data: TIssueWorkLogPayload) => Promise<void>;
  onCancel?: () => void;
};

export function WorkLogForm(props: Props) {
  const { projectId, initialValue, onSubmit, onCancel } = props;
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  // the person the time is booked for; defaults to the current user
  const [loggedBy, setLoggedBy] = useState<string | null>(initialValue?.logged_by ?? currentUser?.id ?? null);
  const [duration, setDuration] = useState(initialValue ? minutesToInput(initialValue.duration) : "");
  const [date, setDate] = useState<string>(initialValue?.date ?? renderFormattedPayloadDate(new Date()) ?? "");
  const [description, setDescription] = useState(initialValue?.description ?? "");
  const [hasError, setHasError] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const minutes = parseDurationToMinutes(duration);
    if (minutes === null) {
      setHasError(true);
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmit({
        duration: minutes,
        date,
        description: description.trim(),
        logged_by: loggedBy ?? currentUser?.id ?? "",
      });
      if (!initialValue) {
        setDuration("");
        setDescription("");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 rounded-md border border-subtle p-2">
      <div className="flex flex-wrap items-start gap-2">
        <div className="flex w-36 flex-col gap-1">
          <Input
            aria-label={t("worklog.duration")}
            value={duration}
            onChange={(e) => {
              setDuration(e.target.value);
              setHasError(false);
            }}
            placeholder={t("worklog.duration_placeholder")}
            hasError={hasError}
            className="w-full"
          />
        </div>
        <div className="h-8">
          <DateDropdown
            value={date}
            onChange={(val) => setDate(renderFormattedPayloadDate(val ?? new Date()) ?? date)}
            buttonVariant="border-with-text"
            placeholder={t("worklog.date")}
            maxDate={new Date()}
          />
        </div>
        <div className="h-8">
          <MemberDropdown
            projectId={projectId}
            value={loggedBy}
            onChange={(val) => setLoggedBy(val ?? currentUser?.id ?? null)}
            multiple={false}
            buttonVariant="border-with-text"
            placeholder={t("worklog.user")}
            showUserDetails
          />
        </div>
        <Input
          aria-label={t("worklog.description")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t("worklog.description_placeholder")}
          className="min-w-48 flex-1"
        />
      </div>
      {hasError && <p className="text-12 text-danger-primary">{t("worklog.invalid_duration")}</p>}
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button variant="secondary" size="sm" type="button" onClick={onCancel}>
            {t("worklog.cancel")}
          </Button>
        )}
        <Button variant="primary" size="sm" type="submit" loading={isSubmitting}>
          {initialValue ? t("worklog.save") : t("worklog.add")}
        </Button>
      </div>
    </form>
  );
}
