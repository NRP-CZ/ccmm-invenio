import React from "react";
import { buildUID } from "react-searchkit";
import Overridable from "react-overridable";
import { i18next } from "@translations/ccmm_invenio";
import { UppyUploader } from "@js/invenio_rdm_records";

export const CCMMFiles = {
  key: "files",
  label: i18next.t("Upload files"),
  component: (tabConfig) => {
    const { record, formConfig } = tabConfig;
    const { filesLocked, permissions } = formConfig.config;
    const { overridableIdPrefix } = formConfig;
    return (
      <Overridable id={buildUID(overridableIdPrefix, "Files")} {...tabConfig}>
        <UppyUploader
          isDraftRecord={!record.is_published}
          config={formConfig}
          quota={formConfig.quota}
          decimalSizeDisplay={formConfig.decimal_size_display}
          allowEmptyFiles={formConfig.allow_empty_files}
          fileUploadConcurrency={formConfig.file_upload_concurrency}
          showMetadataOnlyToggle={permissions?.can_manage_files}
          filesLocked={filesLocked}
        />
      </Overridable>
    );
  },
  includesPaths: ["files.enabled"],
};
