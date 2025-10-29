<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/" xmlns:ns0="http://www.w3.org/ns/dcat#" xmlns:ns1="http://purl.org/dc/terms/" xmlns:ns2="https://techlib.cz/vocabulary/ccmm/" xmlns:ns3="http://www.w3.org/ns/locn#">
  <xsl:import href="../location-relation-type/lifting.xslt"/>
  <xsl:output method="xml" version="1.0" encoding="utf-8" media-type="application/rdf+xml" indent="yes"/>
  <xsl:template match="/location">
    <rdf:RDF>
      <xsl:variable name="result">
        <xsl:sequence>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235167407-c0c8-51f4-be0a"/>
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
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235167407-c0c8-51f4-be0a">
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
      <rdf:type rdf:resource="https://techlib.cz/vocabulary/datacite/Geolocation"/>
      <xsl:copy-of select="$arc"/>
      <xsl:for-each select="bbox">
        <ns0:bbox rdf:datatype="http://www.w3.org/2000/01/rdf-schema#Literal">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:bbox>
      </xsl:for-each>
      <xsl:for-each select="location_name">
        <ns1:title rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns1:title>
      </xsl:for-each>
      <xsl:for-each select="location_relation_type">
        <ns2:hasType>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1747685228117-d1d5-c203-b159"/>
        </ns2:hasType>
      </xsl:for-each>
      <xsl:for-each select="geometry">
        <ns3:geometry>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742340936467-5d87-fae6-b5c7"/>
        </ns3:geometry>
      </xsl:for-each>
      <xsl:for-each select="related_object">
        <ns2:hasRelatedResource>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234428662-255b-ab44-995e"/>
        </ns2:hasRelatedResource>
      </xsl:for-each>
    </rdf:Description>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
