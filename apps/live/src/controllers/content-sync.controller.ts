/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// custom: fork extension - replaces page content/title from the public pages API.

import type { Hocuspocus } from "@hocuspocus/server";
import type { Request, Response } from "express";
import * as Y from "yjs";
import { z } from "zod";
// plane imports
import { Controller, Middleware, Post } from "@plane/decorators";
import {
  convertBase64StringToBinaryData,
  getAllDocumentFormatsFromDocumentEditorBinaryData,
  getBinaryDataFromDocumentEditorHTMLString,
} from "@plane/editor";
import { logger } from "@plane/logger";
// lib
import { requireSecretKey } from "@/lib/auth-middleware";

const contentSyncSchema = z
  .object({
    page_id: z.string().uuid(),
    // current persisted state, used when the document is not loaded in memory
    description_binary: z.string().nullable().optional(),
    current_description_html: z.string().nullable().optional(),
    current_name: z.string().nullable().optional(),
    // new values; at least one is required
    description_html: z.string().optional(),
    name: z.string().optional(),
  })
  .refine((data) => data.description_html !== undefined || data.name !== undefined, {
    message: "description_html or name is required",
  });

type TContentSyncBody = z.infer<typeof contentSyncSchema>;

const CONTENT_FIELD = "default";
const TITLE_FIELD = "title";

/**
 * Deep copy of an XML node. Y.XmlElement#clone() only keeps string attributes and would
 * drop numeric ones such as the heading level, so attributes and text deltas are copied here.
 */
const cloneNode = (node: Y.XmlElement | Y.XmlText): Y.XmlElement | Y.XmlText => {
  if (node instanceof Y.XmlText) {
    const text = new Y.XmlText();
    text.applyDelta(node.toDelta());
    return text;
  }
  const element = new Y.XmlElement(node.nodeName);
  Object.entries(node.getAttributes()).forEach(([key, value]) => element.setAttribute(key, value as string));
  element.insert(
    0,
    node.toArray().map((child) => cloneNode(child as Y.XmlElement | Y.XmlText))
  );
  return element;
};

/**
 * Replace all children of `field` in `target` with copies of the same field from `source`.
 * Runs as regular Yjs operations, so connected editors and their local (IndexedDB) copies
 * receive proper deletions instead of a conflicting second document.
 */
const replaceFragment = (target: Y.Doc, source: Y.Doc, field: string) => {
  const targetFragment = target.getXmlFragment(field);
  const sourceNodes = source
    .getXmlFragment(field)
    .toArray()
    .map((node) => cloneNode(node as Y.XmlElement | Y.XmlText));
  targetFragment.delete(0, targetFragment.length);
  targetFragment.insert(0, sourceNodes);
};

const buildSourceDoc = (html: string, title: string): Y.Doc => {
  const source = new Y.Doc();
  Y.applyUpdate(source, getBinaryDataFromDocumentEditorHTMLString(html, title));
  return source;
};

/** Load the persisted state into a detached Y.Doc when the page is not open anywhere. */
const loadDetachedDoc = (body: TContentSyncBody): Y.Doc => {
  if (body.description_binary) {
    const doc = new Y.Doc();
    Y.applyUpdate(doc, new Uint8Array(convertBase64StringToBinaryData(body.description_binary)));
    return doc;
  }
  return buildSourceDoc(body.current_description_html ?? "<p></p>", body.current_name ?? "");
};

const applyChanges = (doc: Y.Doc, body: TContentSyncBody) => {
  const source = buildSourceDoc(body.description_html ?? "<p></p>", body.name ?? "");
  doc.transact(() => {
    if (body.description_html !== undefined) replaceFragment(doc, source, CONTENT_FIELD);
    if (body.name !== undefined) replaceFragment(doc, source, TITLE_FIELD);
  });
};

@Controller("/content-sync")
export class ContentSyncController {
  [key: string]: unknown;
  private readonly hocusPocusServer: Hocuspocus;

  constructor(hocusPocusServer: Hocuspocus) {
    this.hocusPocusServer = hocusPocusServer;
  }

  @Post("/")
  @Middleware(requireSecretKey)
  async syncContent(req: Request, res: Response) {
    const parsed = contentSyncSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ message: "Validation error", errors: parsed.error.errors });
    }
    const body = parsed.data;

    try {
      // A loaded document is shared with connected editors: change it in place so the
      // update is broadcast and later persisted by the regular store hook.
      const liveDocument = this.hocusPocusServer.documents.get(body.page_id);
      const doc = liveDocument ?? loadDetachedDoc(body);
      applyChanges(doc, body);

      const { contentBinaryEncoded, contentHTML, contentJSON } = getAllDocumentFormatsFromDocumentEditorBinaryData(
        Y.encodeStateAsUpdate(doc),
        true
      );
      return res.status(200).json({
        description_binary: contentBinaryEncoded,
        description_html: contentHTML,
        description_json: contentJSON,
        was_loaded: Boolean(liveDocument),
      });
    } catch (error) {
      logger.error("CONTENT_SYNC_CONTROLLER: failed to apply content", error);
      return res.status(500).json({ message: "Internal server error." });
    }
  }
}
