import React from "react";
import { buildUID } from "react-searchkit";
import Overridable from "react-overridable";
import { i18next } from "@translations/ccmm_invenio";
import { FundingField } from "@js/oarepo_ui/forms";

export const CCMMFunding = {
  key: "funding",
  label: i18next.t("Funding"),
  component: (tabConfig) => {
    const { overridableIdPrefix } = tabConfig.formConfig;
    return (
      <Overridable
        id={buildUID(overridableIdPrefix, "Funding")}
        {...tabConfig}
      >
        <FundingField fieldPath="metadata.funding" />
      </Overridable>
    );
  },
  includesPaths: ["metadata.funding"],
};
