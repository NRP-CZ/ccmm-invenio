<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/" xmlns:ns0="r" xmlns:ns1="i" xmlns:ns2="q" xmlns:ns3="h">
  <xsl:import href="../resource-to-agent-relationship/lifting.xslt"/>
  <xsl:output method="xml" version="1.0" encoding="utf-8" media-type="application/rdf+xml" indent="yes"/>
  <xsl:template match="/resource">
    <rdf:RDF>
      <xsl:variable name="result">
        <xsl:sequence>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234428662-255b-ab44-995e"/>
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
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234428662-255b-ab44-995e">
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
      <rdf:type rdf:resource="http://www.w3.org/2000/01/rdf-schema#Resource"/>
      <xsl:copy-of select="$arc"/>
      <xsl:for-each select="relationType">
        <ns0:elationType rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:elationType>
      </xsl:for-each>
      <xsl:for-each select="type">
        <ns0:esourceType rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:esourceType>
      </xsl:for-each>
      <xsl:for-each select="title">
        <ns0:elatedItemTitle rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:elatedItemTitle>
      </xsl:for-each>
      <xsl:for-each select="identifier">
        <ns1:dentifier rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns1:dentifier>
      </xsl:for-each>
      <xsl:for-each select="qualified_relation">
        <ns2:ualifiedRelation>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235557653-64a2-513a-97fe"/>
        </ns2:ualifiedRelation>
      </xsl:for-each>
      <xsl:for-each select="time_reference">
        <ns3:asTimeReference>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235299937-b17d-6f34-926d"/>
        </ns3:asTimeReference>
      </xsl:for-each>
    </rdf:Description>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
