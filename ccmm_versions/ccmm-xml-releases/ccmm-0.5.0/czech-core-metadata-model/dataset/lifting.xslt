<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/" xmlns:ns0="r" xmlns:ns1="http://www.w3.org/ns/dcat#" xmlns:ns2="http://purl.org/dc/terms/" xmlns:ns3="l" xmlns:ns4="h" xmlns:ns5="i" xmlns:ns6="q">
  <xsl:import href="../alternate-title/lifting.xslt"/>
  <xsl:output method="xml" version="1.0" encoding="utf-8" media-type="application/rdf+xml" indent="yes"/>
  <xsl:template match="/dataset">
    <rdf:RDF>
      <xsl:variable name="result">
        <xsl:sequence>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742339877323-9dcc-6a36-988a"/>
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
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742339877323-9dcc-6a36-988a">
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
      <rdf:type rdf:resource="http://www.w3.org/ns/dcat#Dataset"/>
      <xsl:copy-of select="$arc"/>
      <xsl:for-each select="publication_year">
        <ns0:elatedItemPublicationYear rdf:datatype="http://www.w3.org/2001/XMLSchema#gYear">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:elatedItemPublicationYear>
      </xsl:for-each>
      <xsl:for-each select="version">
        <ns1:version rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns1:version>
      </xsl:for-each>
      <xsl:for-each select="description">
        <ns2:description>
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns2:description>
      </xsl:for-each>
      <xsl:for-each select="other_language">
        <ns3:anguage rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns3:anguage>
      </xsl:for-each>
      <xsl:for-each select="primary_language">
        <ns3:anguage rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns3:anguage>
      </xsl:for-each>
      <xsl:for-each select="resource_type">
        <ns0:esourceType rdf:datatype="http://www.w3.org/2001/XMLSchema#string">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns0:esourceType>
      </xsl:for-each>
      <xsl:for-each select="title">
        <ns2:title rdf:datatype="http://www.w3.org/1999/02/22-rdf-syntax-ns#langString">
          <xsl:apply-templates select="@*"/>
          <xsl:value-of select="."/>
        </ns2:title>
      </xsl:for-each>
      <xsl:for-each select="alternate_title">
        <ns4:asAlternateTitle>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742340187136-c36a-9f4c-b745"/>
        </ns4:asAlternateTitle>
      </xsl:for-each>
      <xsl:for-each select="is_described_by">
        <ns5:sDescribedBy>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742339770114-2bc2-3bdc-a309"/>
        </ns5:sDescribedBy>
      </xsl:for-each>
      <xsl:for-each select="identifier">
        <ns4:asIdentifier>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742340169817-84a9-ded1-a656"/>
        </ns4:asIdentifier>
      </xsl:for-each>
      <xsl:for-each select="location">
        <ns2:spatial>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235167407-c0c8-51f4-be0a"/>
        </ns2:spatial>
      </xsl:for-each>
      <xsl:for-each select="provenance">
        <ns2:provenance>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742288763165-c843-1e73-9f91"/>
        </ns2:provenance>
      </xsl:for-each>
      <xsl:for-each select="qualified_relation">
        <ns6:ualifiedRelation>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235557653-64a2-513a-97fe"/>
        </ns6:ualifiedRelation>
      </xsl:for-each>
      <xsl:for-each select="time_reference">
        <ns4:asTimeReference>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235299937-b17d-6f34-926d"/>
        </ns4:asTimeReference>
      </xsl:for-each>
      <xsl:for-each select="subject">
        <ns4:asSubject>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742338662847-61c1-8d4b-b552"/>
        </ns4:asSubject>
      </xsl:for-each>
      <xsl:for-each select="validation_result">
        <ns4:asValidationResult>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742288707998-704b-3f0e-8e1a"/>
        </ns4:asValidationResult>
      </xsl:for-each>
      <xsl:for-each select="distribution">
        <ns4:asDistribution>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234358899-6443-fe0d-803b"/>
        </ns4:asDistribution>
      </xsl:for-each>
      <xsl:for-each select="funding_reference">
        <ns4:asFundingReference>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235374506-6369-b2fd-b1bf"/>
        </ns4:asFundingReference>
      </xsl:for-each>
      <xsl:for-each select="terms_of_use">
        <ns4:asVersion>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235510107-a209-3731-aa0c"/>
        </ns4:asVersion>
      </xsl:for-each>
      <xsl:for-each select="related_resource">
        <ns4:asRelatedResource>
          <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234428662-255b-ab44-995e"/>
        </ns4:asRelatedResource>
      </xsl:for-each>
    </rdf:Description>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
