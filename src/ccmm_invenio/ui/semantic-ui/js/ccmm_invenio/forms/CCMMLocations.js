import React from "react";
import Overridable from "react-overridable";
import { buildUID } from "react-searchkit";
import { i18next } from "@translations/ccmm_invenio";
import { LocationsInputField } from "./LocationsInputField/components/LocationsInputField";

export const CCMMLocations = {
  key: "locations",
  label: i18next.t("Geographic locations"),

  component: (tabConfig) => {
    const { formConfig } = tabConfig;
    const { overridableIdPrefix } = formConfig;
    const {
      vocabularies: {
        identifiers: { scheme },
      },
    } = formConfig.config;

    return (
      <Overridable
        id={buildUID(overridableIdPrefix, "locations")}
        {...tabConfig}
      >
        <LocationsInputField
          fieldPath="metadata.locations"
          label={i18next.t("Geographic locations")}
          icon="map marker alternate"
          identifiersScheme={scheme}
        />
      </Overridable>
    );
  },

  includesPaths: ["metadata.locations"],
};
