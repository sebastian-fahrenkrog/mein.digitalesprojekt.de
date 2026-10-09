/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CollaborationController } from "./collaboration.controller";
// custom: fork extension
import { ContentSyncController } from "./content-sync.controller";
import { DocumentController } from "./document.controller";
import { HealthController } from "./health.controller";
import { PdfExportController } from "./pdf-export.controller";

export const CONTROLLERS = [
  CollaborationController,
  DocumentController,
  HealthController,
  PdfExportController,
  ContentSyncController, // custom: fork extension
];
