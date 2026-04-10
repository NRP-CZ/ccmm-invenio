import React from "react";
import { buildUID } from "react-searchkit";
import Overridable from "react-overridable";
import { i18next } from "@translations/ccmm_invenio";
import _get from "lodash/get";
import { EDTFSingleDatePicker, CreatibutorsField } from "@js/oarepo_ui/forms";
import {
  TitlesField,
  LanguagesField,
  ResourceTypeField,
  PublisherField,
  VersionField,
  LicenseField,
  SubjectsField,
  DatesField,
} from "@js/invenio_rdm_records";
import { AdditionalDescriptionsField } from "@js/invenio_rdm_records/src/deposit/fields/DescriptionsField/components";

export const CCMMGeneralInformation = {
  key: "general-information",
  label: i18next.t("General information"),
  component: (tabConfig) => {
    const { record, formConfig } = tabConfig;
    const { vocabularies } = formConfig.config;
    const { overridableIdPrefix } = formConfig;
    return (
      <>
        <Overridable
          id={buildUID(overridableIdPrefix, "Title")}
          {...tabConfig}
        >
          <TitlesField
            options={vocabularies?.titles}
            fieldPath="metadata.title"
            recordUI={record.ui}
            required
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Creators")}
          {...tabConfig}
        >
          <CreatibutorsField
            fieldPath="metadata.creators"
            schema="creators"
            autocompleteNames="search"
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Contributors")}
          {...tabConfig}
        >
          <CreatibutorsField
            fieldPath="metadata.contributors"
            schema="contributors"
            autocompleteNames="search"
            showRoleField
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "PublicationDate")}
          {...tabConfig}
        >
          <EDTFSingleDatePicker fieldPath="metadata.publication_date" />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Publisher")}
          {...tabConfig}
        >
          <PublisherField fieldPath="metadata.publisher" />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Version")}
          {...tabConfig}
        >
          <VersionField fieldPath="metadata.version" />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "ResourceType")}
          {...tabConfig}
        >
          <ResourceTypeField
            options={vocabularies?.resource_type}
            fieldPath="metadata.resource_type"
            required
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Languages")}
          {...tabConfig}
        >
          <LanguagesField
            fieldPath="metadata.languages"
            initialOptions={_get(record, "ui.languages", []).filter(
              (lang) => lang !== null,
            )}
            serializeSuggestions={(suggestions) =>
              suggestions.map((item) => ({
                text: item.title_l10n,
                value: item.id,
                key: item.id,
              }))
            }
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Subjects")}
          {...tabConfig}
        >
          <SubjectsField
            fieldPath="metadata.subjects"
            initialOptions={_get(record, "ui.subjects", null)}
            limitToOptions={vocabularies?.subjects?.limit_to}
            searchOnFocus
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Rights")}
          {...tabConfig}
        >
          <LicenseField
            fieldPath="metadata.rights"
            searchConfig={{
              searchApi: {
                axios: {
                  headers: {
                    Accept: "application/vnd.inveniordm.v1+json",
                  },
                  url: "/api/vocabularies/licenses",
                  withCredentials: false,
                },
              },
              initialQueryState: {
                filters: [["tags", "recommended"]],
                sortBy: "bestmatch",
                sortOrder: "asc",
                layout: "list",
                page: 1,
                size: 12,
              },
            }}
            serializeLicenses={(result) => ({
              title: result.title_l10n,
              description: result.description_l10n,
              id: result.id,
              link: result.props.url,
            })}
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "Dates")}
          {...tabConfig}
        >
          <DatesField
            fieldPath="metadata.dates"
            options={vocabularies?.dates}
            showEmptyValue
          />
        </Overridable>
        <Overridable
          id={buildUID(overridableIdPrefix, "AdditionalDescriptions")}
          {...tabConfig}
        >
          <AdditionalDescriptionsField
            recordUI={_get(record, "ui", null)}
            options={vocabularies?.descriptions}
            optimized
            fieldPath="metadata.additional_descriptions"
            values={record}
          />
        </Overridable>
      </>
    );
  },
  includesPaths: [
    "metadata.title",
    "metadata.creators",
    "metadata.contributors",
    "metadata.publication_date",
    "metadata.publisher",
    "metadata.version",
    "metadata.resource_type",
    "metadata.languages",
    "metadata.subjects",
    "metadata.rights",
    "metadata.dates",
    "metadata.additional_descriptions",
  ],
};
