import React from "react";
import PropTypes from "prop-types";
import { Grid, Menu } from "semantic-ui-react";
import { i18next } from "@translations/ccmm_invenio";

const apiConfigShape = PropTypes.shape({
  appId: PropTypes.string.isRequired,
  initialQueryState: PropTypes.object.isRequired,
  searchApi: PropTypes.object.isRequired,
  toggleText: PropTypes.string,
});

// allCommunities slot is the initial active tab in upstream CommunitySelectionSearch,
// so the my-communities config goes there to make "My communities" the default tab
// without overriding the parent's initial state.
export const swappedApiConfigs = {
  allCommunities: {
    initialQueryState: { size: 5, page: 1, sortBy: "bestmatch" },
    searchApi: {
      axios: {
        url: "/api/user/communities",
        headers: { Accept: "application/vnd.inveniordm.v1+json" },
      },
    },
    appId: "CCMM.CommunitySelectionSearch.MyCommunities",
    toggleText: i18next.t("Search in my communities"),
  },
  myCommunities: {
    initialQueryState: { size: 5, page: 1, sortBy: "bestmatch" },
    searchApi: {
      axios: {
        url: "/api/communities",
        headers: { Accept: "application/vnd.inveniordm.v1+json" },
      },
    },
    appId: "CCMM.CommunitySelectionSearch.AllCommunities",
    toggleText: i18next.t("Search in all communities"),
  },
};

const ReversedTabMenu = ({
  allCommunities,
  myCommunities,
  selectedAppId,
  onSelectConfig,
  myCommunitiesEnabled,
}) =>
  myCommunitiesEnabled && (
    <Grid.Column
      mobile={16}
      tablet={8}
      computer={8}
      textAlign="left"
      floated="left"
      className="pt-0 pl-0"
    >
      <Menu role="tablist" className="theme-primary-menu" compact>
        <Menu.Item
          as="button"
          role="tab"
          id="my-communities-tab"
          aria-selected={selectedAppId === allCommunities.appId}
          aria-controls={allCommunities.appId}
          name="My communities"
          active={selectedAppId === allCommunities.appId}
          onClick={() => onSelectConfig(allCommunities)}
        >
          {i18next.t("My communities")}
        </Menu.Item>
        <Menu.Item
          as="button"
          role="tab"
          id="all-communities-tab"
          aria-selected={selectedAppId === myCommunities.appId}
          aria-controls={myCommunities.appId}
          name="All"
          active={selectedAppId === myCommunities.appId}
          onClick={() => onSelectConfig(myCommunities)}
        >
          {i18next.t("All")}
        </Menu.Item>
      </Menu>
    </Grid.Column>
  );

ReversedTabMenu.propTypes = {
  allCommunities: apiConfigShape.isRequired,
  myCommunities: apiConfigShape.isRequired,
  selectedAppId: PropTypes.string.isRequired,
  onSelectConfig: PropTypes.func.isRequired,
  myCommunitiesEnabled: PropTypes.bool.isRequired,
};

export const communitySelectionOverrides = {
  "InvenioRdmRecords.CommunityHeader.CommunitySelectionSearch.TabMenu.Container":
    ReversedTabMenu,
};
