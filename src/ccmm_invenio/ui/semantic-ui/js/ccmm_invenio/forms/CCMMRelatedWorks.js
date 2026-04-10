import React from "react";
import { buildUID } from "react-searchkit";
import Overridable from "react-overridable";
import { i18next } from "@translations/ccmm_invenio";
import { RelatedResourceField } from "./RelatedResourceField";

export const CCMMRelatedWorks = {
  key: "related-works",
  label: i18next.t("Related works"),
  component: (tabConfig) => {
    const { record, formConfig } = tabConfig;
    const { overridableIdPrefix } = formConfig;
    return (
      <Overridable
        id={buildUID(overridableIdPrefix, "RelatedResources")}
        {...tabConfig}
      >
        <RelatedResourceField
          fieldPath="metadata.related_resources"
          relatedResourceUI={record.ui?.related_resources}
        />
      </Overridable>
    );
  },
  includesPaths: ["metadata.related_resources"],
};
