import React from "react";
import PropTypes from "prop-types";
import { i18next } from "@translations/ccmm_invenio";

const MAX_CREATORS = 5;

const formatCreator = (creator) => {
  const p = creator?.person_or_org;
  if (!p) return null;
  if (p.family_name) {
    const family = p.family_name.toUpperCase();
    const given = p.given_name?.trim();
    return given ? `${family}, ${given[0].toUpperCase()}.` : family;
  }
  if (p.name) return p.name.toUpperCase();
  return null;
};

const formatCreators = (creators) => {
  if (!creators?.length) return "";
  const formatted = creators
    .slice(0, MAX_CREATORS)
    .map(formatCreator)
    .filter(Boolean);
  if (formatted.length === 0) return "";
  let joined;
  if (formatted.length === 1) {
    joined = formatted[0];
  } else {
    const head = formatted.slice(0, -1).join(", ");
    const tail = formatted[formatted.length - 1];
    joined = `${head} ${i18next.t("and")} ${tail}`;
  }
  if (creators.length > MAX_CREATORS) joined += " et al.";
  return joined;
};

const extractYear = (date) => {
  if (!date) return "";
  const match = String(date).match(/^(\d{4})/);
  return match ? match[1] : "";
};


export const RelatedResourceCitation = ({ resource, relationTypeLabel }) => {
  if (!resource) return null;

  const creators = formatCreators(resource.creators);
  const year = extractYear(resource.publication_date);
  const title = resource.title || i18next.t("Untitled resource");
  const publisher = resource.publisher;
  const sourceUrl = resource.imported;
  const isOnline = Boolean(sourceUrl);

  const head = [creators, year].filter(Boolean).join(", ");

  return (
    <span className="related-resource-citation">
      {head && <span>{head}. </span>}
      <span className="related-resource-citation__title">
        {title}
        {isOnline && ` [${i18next.t("online")}]`}.
      </span>
      {publisher && <span> {publisher}.</span>}
      {sourceUrl && (
        <span>
          {" "}
          {i18next.t("Available at")}:{" "}
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            {sourceUrl}
          </a>
          .
        </span>
      )}
      {relationTypeLabel && (
        <span> [{relationTypeLabel.toLowerCase()}]</span>
      )}
    </span>
  );
};

RelatedResourceCitation.propTypes = {
  resource: PropTypes.object.isRequired,
  relationTypeLabel: PropTypes.string,
};
