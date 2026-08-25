import React from "react";
import { buildUID } from "react-searchkit";
import Overridable from "react-overridable";
import { i18next } from "@translations/ccmm_invenio";
import { IdentifiersField } from "@js/invenio_rdm_records";

export const CCMMAlternativeIdentifiers = {
  key: "alternative-identifiers",
  label: i18next.t("Alternative identifiers"),
  component: (tabConfig) => {
    const { formConfig } = tabConfig;
    const { vocabularies } = formConfig.config;
    const { overridableIdPrefix } = formConfig;
    return (
      <Overridable
        id={buildUID(overridableIdPrefix, "Identifiers")}
        {...tabConfig}
      >
        <IdentifiersField
          fieldPath="metadata.identifiers"
          label={i18next.t("Alternative identifiers")}
          labelIcon="barcode"
          schemeOptions={vocabularies?.identifiers?.scheme}
          showEmptyValue
        />
      </Overridable>
    );
  },
  includesPaths: ["metadata.identifiers"],
};
