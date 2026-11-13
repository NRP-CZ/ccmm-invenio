// SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
// SPDX-License-Identifier: MIT

import { CCMMCommunityAndAccess } from "./CCMMCommunityAndAccess";
import { CCMMFiles } from "./CCMMFiles";
import { CCMMGeneralInformation } from "./CCMMGeneralInformation";
import { CCMMFunding } from "./CCMMFunding";
import { CCMMAlternativeIdentifiers } from "./CCMMAlternativeIdentifiers";
import { CCMMRelatedWorks } from "./CCMMRelatedWorks";
import { CCMMLocations } from "./CCMMLocations";

export const CCMMSections = [
  CCMMCommunityAndAccess,
  CCMMFiles,
  CCMMGeneralInformation,
  CCMMFunding,
  CCMMAlternativeIdentifiers,
  CCMMRelatedWorks,
  CCMMLocations,
];
