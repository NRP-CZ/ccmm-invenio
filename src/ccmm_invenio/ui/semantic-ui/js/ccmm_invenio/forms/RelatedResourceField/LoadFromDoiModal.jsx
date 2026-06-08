import React, { useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useMutation } from "@tanstack/react-query";
import {
  Button,
  Form,
  Icon,
  List,
  Message,
  Modal,
  TextArea,
} from "semantic-ui-react";
import { httpApplicationJson } from "@js/oarepo_ui";
import { SchemaField } from "@js/invenio_rdm_records/src/deposit/serializers";
import { i18next } from "@translations/ccmm_invenio";
import { MAX_DOIS_PER_BATCH, collectExistingDois, extractDois } from "./utils";
import { RelatedResourceSchema } from "./RelatedResourceSchema";

// Run the same per-field deserializer the top-level form uses, so imported
// items match the shape Formik already holds for manually-added ones
// (vocab refs flattened to string ids). Otherwise the partial-validation
// merge in Invenio's save flow re-clobbers the deserialized response with
// Formik's un-flattened shape, and the edit dropdown crashes.
const importedItemDeserializer = new SchemaField({
  fieldpath: "metadata.related_resources",
  schema: RelatedResourceSchema,
});

const TEXTAREA_ID = "load-from-doi-input";

const importOne = async (identifier, signal) => {
  const { data } = await httpApplicationJson.post(
    "/api/related-records",
    { identifier },
    { signal }
  );
  return data;
};

export const LoadFromDoiModal = ({
  trigger,
  onResourcesImport,
  existingResources,
  handleSave,
}) => {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [results, setResults] = useState([]);
  const [lastDroppedCount, setLastDroppedCount] = useState(0);
  // Tracks the current in-flight AbortController so the modal can cancel it
  // on close (Close button, X icon, or Esc — all funnel through closeModal).
  const abortRef = useRef(null);

  const existingDoiSet = useMemo(
    () => collectExistingDois(existingResources),
    [existingResources]
  );

  const mutation = useMutation({
    mutationFn: async ({ identifiers, signal }) => {
      const settled = await Promise.allSettled(
        identifiers.map((id) => importOne(id, signal))
      );
      return settled.map((res, idx) => ({
        identifier: identifiers[idx],
        ...(res.status === "fulfilled"
          ? { ok: true, data: res.value }
          : { ok: false, error: res.reason }),
      }));
    },
  });

  const pushImported = (outcomes) => {
    const items = outcomes
      .filter((o) => o.ok)
      .map((o) => ({ ...o.data.metadata, imported_from: o.identifier }));
    if (items.length === 0) return;
    const wrapped = { metadata: { related_resources: items } };
    const imported =
      importedItemDeserializer.deserialize(wrapped).metadata.related_resources;
    onResourcesImport(imported);
  };

  const closeModal = () => {
    // Cancel any in-flight imports — covers Close button, X icon, and Esc
    // (all hit Modal's onClose which calls this).
    // Snapshot before reset: only auto-save when the close happens cleanly
    // (nothing pending) and the user has at least submitted a Load this session.
    // const shouldSave = !mutation.isPending && results.length > 0;
    abortRef.current?.abort();
    abortRef.current = null;
    setOpen(false);
    setInput("");
    setResults([]);
    setLastDroppedCount(0);
    mutation.reset();
    // It seems that save is not necessary now that we have proper UI serialization
    // of related_resources, but leaving this here for now, in case some bug of this type occurs.
    // if (shouldSave) handleSave();
  };

  const normalizeAndCap = (raw) => {
    const all = extractDois(raw);
    const capped = all.slice(0, MAX_DOIS_PER_BATCH);
    setLastDroppedCount(Math.max(0, all.length - MAX_DOIS_PER_BATCH));
    return capped.join("\n");
  };

  const handlePaste = (e) => {
    const pasted = e.clipboardData?.getData("text");
    if (!pasted) return;
    e.preventDefault();
    const el = e.currentTarget;
    const before = el.value.slice(0, el.selectionStart);
    const after = el.value.slice(el.selectionEnd);
    setInput(normalizeAndCap(`${before}\n${pasted}\n${after}`));
  };

  const handleBlur = () => {
    const next = normalizeAndCap(input);
    if (next !== input) setInput(next);
  };

  const currentDois = extractDois(input).slice(0, MAX_DOIS_PER_BATCH);
  const duplicateDois = currentDois.filter((d) => existingDoiSet.has(d));
  const newDois = currentDois.filter((d) => !existingDoiSet.has(d));

  const handleLoad = () => {
    if (newDois.length === 0) return;
    const controller = new AbortController();
    abortRef.current = controller;
    mutation.mutate(
      { identifiers: newDois, signal: controller.signal },
      {
        onSuccess: (outcomes) => {
          if (controller.signal.aborted) return;
          pushImported(outcomes);
          setResults(outcomes);
          const remaining = outcomes
            .filter((o) => !o.ok)
            .map((o) => o.identifier);
          setInput(remaining.join("\n"));
        },
      }
    );
  };

  const errorMessage = (err) => {
    const status = err?.response?.status;
    if (status === 404) {
      return i18next.t(
        "This identifier could not be resolved. Check that the DOI is correct and registered."
      );
    }
    const description = err?.response?.data?.message;
    if (description) return description;
    return err?.message || i18next.t("Unknown error");
  };

  const hasResults = results.length > 0;
  const successCount = results.filter((r) => r.ok).length;
  const failureCount = results.length - successCount;
  const allSucceeded = hasResults && failureCount === 0;

  return (
    <Modal
      centered={false}
      open={open}
      trigger={trigger}
      onOpen={() => setOpen(true)}
      onClose={closeModal}
      closeIcon
      closeOnDimmerClick={false}
      size="small"
    >
      <Modal.Header as="h2" className="pt-10 pb-10">
        {i18next.t("Load resources from DOI")}
      </Modal.Header>
      <Modal.Content scrolling>
        <Form>
          <Form.Field>
            <label htmlFor={TEXTAREA_ID}>
              {i18next.t(
                "Paste one or more DOI URLs (separated by commas, spaces, or new lines). Up to {{max}} DOIs per request — submit additional batches for more.",
                { max: MAX_DOIS_PER_BATCH }
              )}
            </label>
            <TextArea
              id={TEXTAREA_ID}
              rows={4}
              value={input}
              placeholder="https://doi.org/10.1234/abcd, https://doi.org/10.5678/efgh"
              onChange={(e) => setInput(e.target.value)}
              onPaste={handlePaste}
              onBlur={handleBlur}
              disabled={mutation.isPending}
            />
            {lastDroppedCount > 0 && (
              <Message
                warning
                size="tiny"
                data-testid="batch-cap-warning"
                onDismiss={() => setLastDroppedCount(0)}
              >
                {i18next.t(
                  "Only the first {{max}} DOIs were kept; {{dropped}} additional DOI(s) were discarded. Submit this batch, then paste the rest.",
                  { max: MAX_DOIS_PER_BATCH, dropped: lastDroppedCount }
                )}
              </Message>
            )}
            {duplicateDois.length > 0 && (
              <Message negative size="tiny" data-testid="duplicate-doi-warning">
                <Message.Header>
                  {i18next.t(
                    "Already tied to the record (will be skipped on Load):"
                  )}
                </Message.Header>
                <List bulleted>
                  {duplicateDois.map((d) => (
                    <List.Item key={d}>{d}</List.Item>
                  ))}
                </List>
              </Message>
            )}
          </Form.Field>
        </Form>

        {hasResults && (
          <Message
            positive={allSucceeded}
            warning={!allSucceeded && successCount > 0}
            negative={!allSucceeded && successCount === 0}
          >
            <Message.Header>
              {i18next.t("Imported {{success}} of {{total}}", {
                success: successCount,
                total: results.length,
              })}
            </Message.Header>
            <List relaxed>
              {results.map((r) => (
                <List.Item key={r.identifier}>
                  <List.Icon
                    name={r.ok ? "check circle" : "exclamation circle"}
                    color={r.ok ? "green" : "red"}
                  />
                  <List.Content>
                    <List.Header>{r.identifier}</List.Header>
                    {r.ok ? (
                      r.data?.import_errors?.length > 0 && (
                        <List.Description>
                          {i18next.t(
                            "Imported with {{count}} warning(s) — review the entry.",
                            { count: r.data.import_errors.length }
                          )}
                        </List.Description>
                      )
                    ) : (
                      <List.Description>
                        {errorMessage(r.error)}
                      </List.Description>
                    )}
                  </List.Content>
                </List.Item>
              ))}
            </List>
          </Message>
        )}
      </Modal.Content>
      <Modal.Actions>
        <Button
          name="cancel"
          onClick={closeModal}
          icon="remove"
          content={i18next.t("Close")}
          floated="left"
        />
        <Button
          name="load"
          onClick={handleLoad}
          primary
          icon
          labelPosition="left"
          loading={mutation.isPending}
          disabled={mutation.isPending || newDois.length === 0}
        >
          <Icon name="download" />
          {i18next.t("Add to record")}
        </Button>
      </Modal.Actions>
    </Modal>
  );
};

LoadFromDoiModal.propTypes = {
  trigger: PropTypes.node.isRequired,
  onResourcesImport: PropTypes.func.isRequired,
  existingResources: PropTypes.array,
  handleSave: PropTypes.func.isRequired,
};
