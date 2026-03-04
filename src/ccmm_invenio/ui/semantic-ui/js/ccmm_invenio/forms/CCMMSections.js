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

const createSection =
  (overridesFn) => (key, label, includesPaths, renderFn) => ({
    key,
    label,
    includesPaths,
    render: (renderProps) => {
      const overrides = overridesFn?.(renderProps)?.[key] || {};
      return renderFn({ ...renderProps, overrides });
    },
  });

export const createCCMMSections = (overridesFn) => {
  const section = createSection(overridesFn);

  return [
    section("community", i18next.t("Community"), ["parent.communities"],
      ({ initialRecord, formConfig, overrides }) => {
        const { hide_community_selection: hideCommunitySelection } =
          formConfig.config;
        return (
          !hideCommunitySelection && (
            <CommunityHeader
              imagePlaceholderLink="/static/images/square-placeholder.png"
              record={initialRecord}
              {...overrides.CommunityHeader}
            />
          )
        );
      }
    ),

    section("visibility", i18next.t("Visibility"), ["access"],
      ({ record, formConfig, overrides }) => {
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
            {...overrides.AccessRightField}
          />
        );
      }
    ),

    section("files", i18next.t("Files upload"), ["files.enabled"],
      ({ record, formConfig, overrides }) => {
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
            {...overrides.UppyUploader}
          />
        );
      }
    ),

    section(
      "basic-information",
      i18next.t("Basic information"),
      [
        "metadata.title",
        "metadata.resource_type",
        "metadata.publication_date",
        "metadata.additional_descriptions",
        "metadata.languages",
        "metadata.publisher",
        "metadata.rights",
      ],
      ({ record, formConfig, overrides }) => {
        const { vocabularies } = formConfig.config;
        return (
          <>
            <TitlesField
              options={vocabularies?.titles || []}
              fieldPath="metadata.title"
              recordUI={record.ui}
              required
              {...overrides.TitlesField}
            />
            <ResourceTypeField
              options={vocabularies?.resource_type || []}
              fieldPath="metadata.resource_type"
              required
              {...overrides.ResourceTypeField}
            />
            <EDTFSingleDatePicker
              fieldPath="metadata.publication_date"
              {...overrides.EDTFSingleDatePicker}
            />
            <AdditionalDescriptionsField
              recordUI={_get(record, "ui", null)}
              options={vocabularies?.descriptions || []}
              optimized
              fieldPath="metadata.additional_descriptions"
              values={record}
              {...overrides.AdditionalDescriptionsField}
            />
            <LanguagesField
              fieldPath="metadata.languages"
              initialOptions={_get(record, "ui.languages", []).filter(
                (lang) => lang !== null
              )}
              serializeSuggestions={(suggestions) =>
                suggestions.map((item) => ({
                  text: item.title_l10n,
                  value: item.id,
                  key: item.id,
                }))
              }
              {...overrides.LanguagesField}
            />
            <PublisherField
              fieldPath="metadata.publisher"
              {...overrides.PublisherField}
            />
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
              {...overrides.LicenseField}
            />
          </>
        );
      }
    ),

    section(
      "creators-contributors",
      i18next.t("Creators and Contributors"),
      ["metadata.creators", "metadata.contributors"],
      ({ overrides }) => (
        <>
          <CreatibutorsField
            fieldPath="metadata.creators"
            schema="creators"
            autocompleteNames="search"
            {...overrides.CreatorsField}
          />
          <CreatibutorsField
            fieldPath="metadata.contributors"
            schema="contributors"
            autocompleteNames="search"
            showRoleField
            {...overrides.ContributorsField}
          />
        </>
      )
    ),

    section(
      "recommended-information",
      i18next.t("Recommended information"),
      ["metadata.version", "metadata.subjects", "metadata.dates"],
      ({ record, formConfig, overrides }) => {
        const { vocabularies } = formConfig.config;
        return (
          <>
            <VersionField
              fieldPath="metadata.version"
              {...overrides.VersionField}
            />
            <SubjectsField
              fieldPath="metadata.subjects"
              initialOptions={_get(record, "ui.subjects", []).filter(
                (subject) => subject !== null
              )}
              limitToOptions={vocabularies?.subjects?.limit_to || []}
              searchOnFocus
              {...overrides.SubjectsField}
            />
            <DatesField
              fieldPath="metadata.dates"
              options={vocabularies?.dates || []}
              showEmptyValue
              {...overrides.DatesField}
            />
          </>
        );
      }
    ),

    section(
      "identifiers",
      i18next.t("Identifiers"),
      ["metadata.identifiers", "metadata.funding"],
      ({ formConfig, overrides }) => {
        const { vocabularies } = formConfig.config;
        return (
          <>
            <IdentifiersField
              fieldPath="metadata.identifiers"
              label={i18next.t("Alternate identifiers")}
              labelIcon="barcode"
              schemeOptions={vocabularies?.identifiers?.scheme || []}
              showEmptyValue
              {...overrides.IdentifiersField}
            />
            <FundingField
              fieldPath="metadata.funding"
              {...overrides.FundingField}
            />
          </>
        );
      }
    ),

    section(
      "related-resources",
      i18next.t("Related resources"),
      ["metadata.related_resources"],
      ({ record, overrides }) => (
        <RelatedResourceField
          fieldPath="metadata.related_resources"
          relatedResourceUI={record.ui?.related_resources}
          {...overrides.RelatedResourceField}
        />
      )
    ),
  ];
};

export const CCMMSections = createCCMMSections();
