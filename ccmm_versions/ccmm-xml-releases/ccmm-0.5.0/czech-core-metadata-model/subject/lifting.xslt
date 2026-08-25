<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/" xmlns:ns0="http://www.w3.org/2004/02/skos/core#" xmlns:ns1="http://purl.org/dc/terms/" xmlns:ns2="https://techlib.cz/vocabulary/datacite/" xmlns:ns3="https://techlib.cz/vocabulary/ccmm/">
  <xsl:import href="../subject-scheme/lifting.xslt"/>
  <xsl:output method="xml" version="1.0" encoding="utf-8" media-type="application/rdf+xml" indent="yes"/>
  <xsl:template match="/subject">
    <rdf:RDF>
      <xsl:variable name="result">
        <xsl:sequence>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742338662847-61c1-8d4b-b552"/>
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
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742338662847-61c1-8d4b-b552">
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
      <rdf:type rdf:resource="https://techlib.cz/vocabulary/datacite/Subject"/>
      <xsl:copy-of select="$arc"/>
      <xsl:for-each select="definition">
        <ns0:definition>
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:definition>
      </xsl:for-each>
      <xsl:for-each select="title">
        <ns1:title rdf:datatype="http://www.w3.org/1999/02/22-rdf-syntax-ns#langString">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns1:title>
      </xsl:for-each>
      <xsl:for-each select="classification_code">
        <ns2:subjectClassificationCode rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns2:subjectClassificationCode>
      </xsl:for-each>
      <xsl:for-each select="scheme">
        <ns3:inSubjectScheme>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742288726417-ccc4-1d84-8bc2"/>
        </ns3:inSubjectScheme>
      </xsl:for-each>
    </rdf:Description>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
