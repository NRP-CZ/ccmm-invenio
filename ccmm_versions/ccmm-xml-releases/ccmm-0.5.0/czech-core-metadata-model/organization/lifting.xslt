<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/" xmlns:ns0="http://xmlns.com/foaf/0.1/" xmlns:ns1="https://techlib.cz/vocabulary/ccmm/" xmlns:ns2="http://www.w3.org/ns/dcat#" xmlns:ns3="http://www.w3.org/2006/vcard/ns#">
  <xsl:import href="../identifier/lifting.xslt"/>
  <xsl:output method="xml" version="1.0" encoding="utf-8" media-type="application/rdf+xml" indent="yes"/>
  <xsl:template match="/organization">
    <rdf:RDF>
      <xsl:variable name="result">
        <xsl:sequence>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744871355397-62d0-acf0-af09"/>
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
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744871355397-62d0-acf0-af09">
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
      <rdf:type rdf:resource="http://www.w3.org/ns/prov#Organization"/>
      <xsl:copy-of select="$arc"/>
      <xsl:for-each select="name">
        <ns0:name rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:name>
      </xsl:for-each>
      <xsl:for-each select="has_identifier">
        <ns1:hasIdentifier>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742340169817-84a9-ded1-a656"/>
        </ns1:hasIdentifier>
      </xsl:for-each>
      <xsl:for-each select="contact_point">
        <ns2:contactPoint>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234373952-7a86-df18-a582"/>
        </ns2:contactPoint>
      </xsl:for-each>
      <xsl:for-each select="alternate_name">
        <ns3:organization-name>
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns3:organization-name>
      </xsl:for-each>
    </rdf:Description>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
