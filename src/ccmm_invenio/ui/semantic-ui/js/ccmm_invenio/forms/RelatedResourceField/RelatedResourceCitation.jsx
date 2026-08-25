import React from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/ccmm_invenio";
import { useSanitizeInput } from "@js/oarepo_ui/forms";
import { extractYear, formatCreators } from "./utils";

// Return `raw` only when it parses as a real URL and uses http(s); otherwise
// "". Blocks javascript:, data:, file:, etc. — browsers will still execute
// `javascript:` in href even though React escapes attribute values.
const safeHref = (raw) => {
  if (!raw) return "";
  try {
    const u = new URL(raw);
    return u.protocol === "https:" || u.protocol === "http:" ? u.href : "";
  } catch {
    return "";
  }
};

// TODO: replace with a proper scheme-aware identifier→URL resolver
// (handle, arxiv, isbn, …) instead of this DOI-only special case.
const doiSourceUrl = (identifiers) => {
  const doi = (identifiers || []).find((i) => i?.scheme === "doi");
  if (!doi?.identifier) return null;
  return /^https?:\/\//i.test(doi.identifier)
    ? doi.identifier
    : `https://doi.org/${doi.identifier}`;
};

export const RelatedResourceCitation = ({ resource }) => {
  const { sanitizeInput } = useSanitizeInput();

  if (!resource) return null;

  const creators = formatCreators(resource.creators);
  const year = extractYear(resource.publication_date);
  const title = resource.title || i18next.t("Untitled resource");
  const publisher = resource.publisher;
  const sourceUrl =
    resource.imported_from || doiSourceUrl(resource.identifiers);
  const sourceHref = safeHref(sourceUrl);
  const isOnline = Boolean(sourceUrl);

  const head = [creators, year].filter(Boolean).join(", ");

  return (
    <span className="related-resource-citation">
      {head && <span>{head}. </span>}
      <span className="related-resource-citation__title">
        <span dangerouslySetInnerHTML={{ __html: sanitizeInput(title) }} />
        {isOnline && ` [${i18next.t("online")}]`}.
      </span>
      {publisher && <span> {publisher}.</span>}
      {sourceUrl && (
        <span>
          {" "}
          {i18next.t("Available at")}:{" "}
          {sourceHref ? (
            <a
              href={sourceHref}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              {sourceUrl}
            </a>
          ) : (
            <span>{sourceUrl}</span>
          )}
          .
        </span>
      )}
    </span>
  );
};

RelatedResourceCitation.propTypes = {
  resource: PropTypes.object.isRequired,
};
