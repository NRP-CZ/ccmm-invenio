import React from "react";
import { buildUID } from "react-searchkit";
import Overridable from "react-overridable";
import { i18next } from "@translations/ccmm_invenio";
import { CommunityHeader, AccessRightField } from "@js/invenio_rdm_records";

export const CCMMCommunityAndAccess = {
  key: "community-and-access",
  label: i18next.t("Community and Access"),
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
  includesPaths: ["parent.communities", "access"],
};
