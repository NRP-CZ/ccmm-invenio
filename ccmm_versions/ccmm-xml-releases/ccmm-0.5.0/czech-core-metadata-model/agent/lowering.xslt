<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:sp="http://www.w3.org/2005/sparql-results#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/">
  <xsl:import href="../identifier/lowering.xslt"/>
  <xsl:output method="xml" version="1.0" encoding="utf-8" indent="yes"/>
  <xsl:param name="subj" select="'s'"/>
  <xsl:param name="pred" select="'p'"/>
  <xsl:param name="obj" select="'o'"/>
  <xsl:variable name="type" select="'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'"/>
  <xsl:function name="c:id-key">
    <xsl:param name="node"/>
    <xsl:value-of select="concat(namespace-uri($node),'|',local-name($node),'|',string($node))"/>
  </xsl:function>
  <xsl:template match="/sp:sparql">
    <xsl:apply-templates select="sp:results/sp:result"/>
  </xsl:template>
  <xsl:template match="sp:result[sp:binding[@name=$pred]/sp:uri/text()=$type and sp:binding[@name=$obj]/sp:uri/text()=&#34;http://xmlns.com/foaf/0.1/Agent&#34;]">
    <agent>
      <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806334636-9353-d66e-89dc">
        <xsl:with-param name="id">
          <xsl:copy-of select="sp:binding[@name=$subj]/*"/>
        </xsl:with-param>
      </xsl:call-template>
    </agent>
  </xsl:template>
  <xsl:template match="sp:result[sp:binding[@name=$pred]/sp:uri/text()=$type and sp:binding[@name=$obj]/sp:uri/text()=&#34;http://www.w3.org/ns/prov#Organization&#34;]">
    <organization>
      <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806345521-602d-5078-a2c5">
        <xsl:with-param name="id">
          <xsl:copy-of select="sp:binding[@name=$subj]/*"/>
        </xsl:with-param>
      </xsl:call-template>
    </organization>
  </xsl:template>
  <xsl:template match="sp:result[sp:binding[@name=$pred]/sp:uri/text()=$type and sp:binding[@name=$obj]/sp:uri/text()=&#34;http://www.w3.org/ns/prov#Person&#34;]">
    <person>
      <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806350501-735b-f599-9019">
        <xsl:with-param name="id">
          <xsl:copy-of select="sp:binding[@name=$subj]/*"/>
        </xsl:with-param>
      </xsl:call-template>
    </person>
  </xsl:template>
  <xsl:template match="@xml:lang">
    <xsl:copy-of select="."/>
  </xsl:template>
  <xsl:template match="sp:literal">
    <xsl:apply-templates select="@*"/>
    <xsl:value-of select="."/>
  </xsl:template>
  <xsl:template match="sp:uri">
    <xsl:value-of select="."/>
  </xsl:template>
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806334636-9353-d66e-89dc">
    <xsl:param name="id"/>
    <xsl:param name="type_name" select="()"/>
    <xsl:param name="no_iri" select="false()"/>
    <xsl:if test="not(empty($type_name))">
      <xsl:attribute name="xsi:type">
        <xsl:value-of select="$type_name"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="not($no_iri)">
      <xsl:for-each select="$id/sp:uri">
        <c:iri>
          <xsl:value-of select="."/>
        </c:iri>
      </xsl:for-each>
    </xsl:if>
    <xsl:variable name="id_test">
      <xsl:value-of select="c:id-key($id/*)"/>
    </xsl:variable>
  </xsl:template>
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806345521-602d-5078-a2c5">
    <xsl:param name="id"/>
    <xsl:param name="type_name" select="()"/>
    <xsl:param name="no_iri" select="false()"/>
    <xsl:if test="not(empty($type_name))">
      <xsl:attribute name="xsi:type">
        <xsl:value-of select="$type_name"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="not($no_iri)">
      <xsl:for-each select="$id/sp:uri">
        <c:iri>
          <xsl:value-of select="."/>
        </c:iri>
      </xsl:for-each>
    </xsl:if>
    <xsl:variable name="id_test">
      <xsl:value-of select="c:id-key($id/*)"/>
    </xsl:variable>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://xmlns.com/foaf/0.1/name&#34;]">
      <name>
        <xsl:apply-templates select="sp:binding[@name=$obj]/sp:literal"/>
      </name>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;https://techlib.cz/vocabulary/ccmm/hasIdentifier&#34;]">
      <has_identifier>
        <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742340169817-84a9-ded1-a656">
          <xsl:with-param name="id">
            <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
          </xsl:with-param>
        </xsl:call-template>
      </has_identifier>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://www.w3.org/ns/dcat#contactPoint&#34;]">
      <contact_point>
        <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234373952-7a86-df18-a582">
          <xsl:with-param name="id">
            <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
          </xsl:with-param>
        </xsl:call-template>
      </contact_point>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://www.w3.org/2006/vcard/ns#organization-name&#34;]">
      <alternate_name>
        <xsl:apply-templates select="sp:binding[@name=$obj]/sp:literal"/>
      </alternate_name>
    </xsl:for-each>
  </xsl:template>
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806350501-735b-f599-9019">
    <xsl:param name="id"/>
    <xsl:param name="type_name" select="()"/>
    <xsl:param name="no_iri" select="false()"/>
    <xsl:if test="not(empty($type_name))">
      <xsl:attribute name="xsi:type">
        <xsl:value-of select="$type_name"/>
      </xsl:attribute>
    </xsl:if>
    <xsl:if test="not($no_iri)">
      <xsl:for-each select="$id/sp:uri">
        <c:iri>
          <xsl:value-of select="."/>
        </c:iri>
      </xsl:for-each>
    </xsl:if>
    <xsl:variable name="id_test">
      <xsl:value-of select="c:id-key($id/*)"/>
    </xsl:variable>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://xmlns.com/foaf/0.1/name&#34;]">
      <name>
        <xsl:apply-templates select="sp:binding[@name=$obj]/sp:literal"/>
      </name>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;https://techlib.cz/vocabulary/ccmm/hasIdentifier&#34;]">
      <has_identifier>
        <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742340169817-84a9-ded1-a656">
          <xsl:with-param name="id">
            <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
          </xsl:with-param>
        </xsl:call-template>
      </has_identifier>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://www.w3.org/ns/dcat#contactPoint&#34;]">
      <contact_point>
        <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742234373952-7a86-df18-a582">
          <xsl:with-param name="id">
            <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
          </xsl:with-param>
        </xsl:call-template>
      </contact_point>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://www.w3.org/2006/vcard/ns#family-name&#34;]">
      <family_name>
        <xsl:apply-templates select="sp:binding[@name=$obj]/sp:literal"/>
      </family_name>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://www.w3.org/2006/vcard/ns#given-name&#34;]">
      <given_name>
        <xsl:apply-templates select="sp:binding[@name=$obj]/sp:literal"/>
      </given_name>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;https://techlib.cz/vocabulary/ccmm/hasAffiliation&#34;]">
      <has_affiliation>
        <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744871355397-62d0-acf0-af09">
          <xsl:with-param name="id">
            <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
          </xsl:with-param>
        </xsl:call-template>
      </has_affiliation>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
