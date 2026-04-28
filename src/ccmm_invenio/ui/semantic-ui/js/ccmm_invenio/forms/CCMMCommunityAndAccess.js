import React from "react";
import { buildUID } from "react-searchkit";
import Overridable from "react-overridable";
import { i18next } from "@translations/ccmm_invenio";
import { CommunityHeader, AccessRightField } from "@js/invenio_rdm_records";
import { computeSectionFilled, isFilled } from "@js/oarepo_ui/forms";
import _get from "lodash/get";

export const CCMMCommunityAndAccess = {
  key: "community-and-access",
  label: i18next.t("Community and Access"),
  saveOnTabChange: true,
  component: (tabConfig) => {
    const { initialRecord, record, formConfig } = tabConfig;
    const {
      hide_community_selection: hideCommunitySelection,
      permissions,
      allowRecordRestriction,
      recordRestrictionGracePeriod,
    } = formConfig.config;
    const { overridableIdPrefix } = formConfig;
    return (
      <>
        {!hideCommunitySelection && (
          <Overridable
            id={buildUID(overridableIdPrefix, "Communities")}
            {...tabConfig}
          >
            <CommunityHeader
              imagePlaceholderLink="/static/images/square-placeholder.png"
              record={initialRecord}
            />
          </Overridable>
        )}
        <Overridable
          id={buildUID(overridableIdPrefix, "Access")}
          {...tabConfig}
        >
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
        </Overridable>
      </>
    );
  },
  sectionFilled: ({ formikValues, reduxState, includesPaths }) => {
    const formikFilled = computeSectionFilled({ formikValues, reduxState, includesPaths });
    const community = _get(reduxState, "deposit.editorState.selectedCommunity");
    const communityFilled = isFilled(community) ? 1 : 0;
    return (formikFilled * includesPaths.length + communityFilled) / (includesPaths.length + 1);
  },
  includesPaths: ["access"],
};
