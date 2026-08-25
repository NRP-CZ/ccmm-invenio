<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/" xmlns:ns0="http://www.w3.org/ns/dcat#" xmlns:ns1="http://purl.org/dc/terms/">
  <xsl:import href="../resource-agent-role-type/lifting.xslt"/>
  <xsl:output method="xml" version="1.0" encoding="utf-8" media-type="application/rdf+xml" indent="yes"/>
  <xsl:template match="/resource_to_agent_relationship">
    <rdf:RDF>
      <xsl:variable name="result">
        <xsl:sequence>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235557653-64a2-513a-97fe"/>
        </xsl:sequence>
      </xsl:variable>
      <xsl:for-each select="$result">
        <xsl:copy>
          <xsl:call-template name="remove-top"/>
        </xsl:copy>
      </xsl:for-each>
      <xsl:for-each select="$result//top-level/node()">
        <xsl:copy>
          <xsl:call-template name="remove-top"/>
        </xsl:copy>
      </xsl:for-each>
    </rdf:RDF>
  </xsl:template>
  <xsl:template match="@xml:lang">
    <xsl:copy-of select="."/>
  </xsl:template>
  <xsl:template name="remove-top">
    <xsl:for-each select="@*">
      <xsl:copy/>
    </xsl:for-each>
    <xsl:for-each select="node()[not(. instance of element(top-level))]">
      <xsl:copy>
        <xsl:call-template name="remove-top"/>
      </xsl:copy>
    </xsl:for-each>
  </xsl:template>
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235557653-64a2-513a-97fe">
    <xsl:param name="arc" select="()"/>
    <xsl:param name="no_iri" select="false()"/>
    <rdf:Description>
      <xsl:apply-templates select="@*"/>
      <xsl:variable name="id">
        <id>
          <xsl:choose>
            <xsl:when test="c:iri and not($no_iri)">
              <xsl:attribute name="rdf:about">
                <xsl:value-of select="c:iri"/>
              </xsl:attribute>
            </xsl:when>
            <xsl:otherwise>
              <xsl:attribute name="rdf:nodeID">
                <xsl:value-of select="generate-id()"/>
              </xsl:attribute>
            </xsl:otherwise>
          </xsl:choose>
        </id>
      </xsl:variable>
      <xsl:copy-of select="$id//@*"/>
      <rdf:type rdf:resource="https://techlib.cz/vocabulary/ccmm/ResourceToAgentRelationship"/>
      <xsl:copy-of select="$arc"/>
      <xsl:for-each select="role">
        <ns0:hadRole>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235606195-b8fa-9b2f-a5cf"/>
        </ns0:hadRole>
      </xsl:for-each>
      <xsl:for-each select="relation">
        <ns1:relation>
          <xsl:variable name="type" select="resolve-QName(@xsi:type,.)"/>
          <xsl:variable name="types">
            <xsl:sequence>
              <agent/>
              <organization/>
              <person/>
            </xsl:sequence>
          </xsl:variable>
          <xsl:choose>
            <xsl:when test="$type=node-name($types/*[1])">
              <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806334636-9353-d66e-89dc"/>
            </xsl:when>
            <xsl:when test="$type=node-name($types/*[2])">
              <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806345521-602d-5078-a2c5"/>
            </xsl:when>
            <xsl:when test="$type=node-name($types/*[3])">
              <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806350501-735b-f599-9019"/>
            </xsl:when>
          </xsl:choose>
        </ns1:relation>
      </xsl:for-each>
    </rdf:Description>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
