import React from "react";
import {
  EDTFSingleDatePicker,
  CreatibutorsField,
  FundingField,
} from "@js/oarepo_ui/forms";
import { i18next } from "@translations/ccmm_invenio";
import _get from "lodash/get";
import {
  UppyUploader,
  TitlesField,
  IdentifiersField,
  LanguagesField,
  ResourceTypeField,
  PublisherField,
  VersionField,
  LicenseField,
  SubjectsField,
  DatesField,
  CommunityHeader,
  AccessRightField,
} from "@js/invenio_rdm_records";
import { AdditionalDescriptionsField } from "@js/invenio_rdm_records/src/deposit/fields/DescriptionsField/components";

import { RelatedResourceField } from "./RelatedResourceField";

export const CCMMSections = [
  {
    key: "community",
    label: i18next.t("Community"),
    render: ({ initialRecord, formConfig }) => {
      const { hide_community_selection: hideCommunitySelection } =
        formConfig.config;
      return (
        !hideCommunitySelection && (
          <CommunityHeader
            imagePlaceholderLink="/static/images/square-placeholder.png"
            record={initialRecord}
          />
        )
      );
    },
    includesPaths: ["parent.communities"],
  },
  {
    key: "visibility",
    label: i18next.t("Visibility"),
    render: ({ record, formConfig }) => {
      const {
        permissions,
        allowRecordRestriction,
        recordRestrictionGracePeriod,
      } = formConfig.config;
      return (
        <AccessRightField
          label={i18next.t("Visibility")}
          record={record}
          labelIcon="shield"
          fieldPath="access"
          showMetadataAccess={permissions?.can_manage_record_access}
          recordRestrictionGracePeriod={recordRestrictionGracePeriod}
          allowRecordRestriction={allowRecordRestriction}
          id="visibility-section"
        />
      );
    },
    includesPaths: ["access"],
  },
  {
    key: "files",
    label: i18next.t("Files upload"),
    render: ({ record, formConfig }) => {
      const { filesLocked } = formConfig.config;
      return (
        <UppyUploader
          isDraftRecord={!record.is_published}
          config={formConfig}
          quota={formConfig.quota}
          decimalSizeDisplay={formConfig.decimal_size_display}
          allowEmptyFiles={formConfig.allow_empty_files}
          fileUploadConcurrency={formConfig.file_upload_concurrency}
          showMetadataOnlyToggle={false}
          filesLocked={filesLocked}
        />
      );
    },
    includesPaths: ["files.enabled"],
  },
  {
    key: "basic-information",
    label: i18next.t("Basic information"),
    render: ({ record, formConfig }) => {
      const { vocabularies } = formConfig.config;
      return (
        <>
          <TitlesField
            options={vocabularies?.titles}
            fieldPath="metadata.title"
            recordUI={record.ui}
            required
          />
          <ResourceTypeField
            options={vocabularies?.resource_type}
            fieldPath="metadata.resource_type"
            required
          />
          <EDTFSingleDatePicker fieldPath="metadata.publication_date" />
          <AdditionalDescriptionsField
            recordUI={_get(record, "ui", null)}
            options={vocabularies?.descriptions}
            optimized
            fieldPath="metadata.additional_descriptions"
            values={record}
          />
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
          <PublisherField fieldPath="metadata.publisher" />
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
        </>
      );
    },
    includesPaths: [
      "metadata.title",
      "metadata.resource_type",
      "metadata.publication_date",
      "metadata.additional_descriptions",
      "metadata.languages",
      "metadata.publisher",
      "metadata.rights",
    ],
  },
  {
    key: "creators-contributors",
    label: i18next.t("Creators and Contributors"),
    render: () => (
      <>
        <CreatibutorsField
          fieldPath="metadata.creators"
          schema="creators"
          autocompleteNames="search"
        />
        <CreatibutorsField
          fieldPath="metadata.contributors"
          schema="contributors"
          autocompleteNames="search"
          showRoleField
        />
      </>
    ),
    includesPaths: ["metadata.creators", "metadata.contributors"],
  },
  {
    key: "recommended-information",
    label: i18next.t("Recommended information"),
    render: ({ record, formConfig }) => {
      const { vocabularies } = formConfig.config;
      return (
        <>
          <VersionField fieldPath="metadata.version" />
          <SubjectsField
            fieldPath="metadata.subjects"
            initialOptions={_get(record, "ui.subjects", null)}
            limitToOptions={vocabularies?.subjects?.limit_to}
            searchOnFocus
          />
          <DatesField
            fieldPath="metadata.dates"
            options={vocabularies?.dates}
            showEmptyValue
          />
        </>
      );
    },
    includesPaths: ["metadata.version", "metadata.subjects", "metadata.dates"],
  },
  {
    key: "identifiers",
    label: i18next.t("Identifiers"),
    render: ({ formConfig }) => {
      const { vocabularies } = formConfig.config;
      return (
        <>
          <IdentifiersField
            fieldPath="metadata.identifiers"
            label={i18next.t("Alternate identifiers")}
            labelIcon="barcode"
            schemeOptions={vocabularies?.identifiers?.scheme}
            showEmptyValue
          />
          <FundingField fieldPath="metadata.funding" />
        </>
      );
    },
    includesPaths: ["metadata.identifiers", "metadata.funding"],
  },
  {
    key: "related-resources",
    label: i18next.t("Related resources"),
    render: ({ record }) => (
      <RelatedResourceField
        fieldPath="metadata.related_resources"
        relatedResourceUI={record.ui?.related_resources}
      />
    ),
    includesPaths: ["metadata.related_resources"],
  },
];
