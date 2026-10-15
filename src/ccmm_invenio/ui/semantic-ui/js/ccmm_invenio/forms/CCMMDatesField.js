import React, { useContext, useMemo } from "react";
import { OverridableContext } from "react-overridable";
import { DatesField } from "@js/invenio_rdm_records";
import { EDTFDaterangePicker } from "@js/oarepo_ui/forms";

// RDM's date input is a free-text EDTF field; default it to the picker, overrides from the app still win
export const CCMMDatesField = (props) => {
  const overrides = useContext(OverridableContext);
  const value = useMemo(
    () => ({
      "InvenioRdmRecords.DepositForm.DatesField.DateField": EDTFDaterangePicker,
      ...overrides,
    }),
    [overrides]
  );
  return (
    <OverridableContext.Provider value={value}>
      <DatesField {...props} />
    </OverridableContext.Provider>
  );
};
