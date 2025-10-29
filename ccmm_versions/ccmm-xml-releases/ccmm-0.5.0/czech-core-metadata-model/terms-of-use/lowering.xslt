<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:sp="http://www.w3.org/2005/sparql-results#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0" xmlns:c="https://schemas.dataspecer.com/xsd/core/">
  <xsl:import href="../access-rights/lowering.xslt"/>
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
  <xsl:template match="sp:result[sp:binding[@name=$pred]/sp:uri/text()=$type and sp:binding[@name=$obj]/sp:uri/text()=&#34;https://techlib.cz/vocabulary/datacite/Rights&#34;]">
    <terms_of_use>
      <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235510107-a209-3731-aa0c">
        <xsl:with-param name="id">
          <xsl:copy-of select="sp:binding[@name=$subj]/*"/>
        </xsl:with-param>
      </xsl:call-template>
    </terms_of_use>
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
  <xsl:template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1742235510107-a209-3731-aa0c">
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
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://purl.org/dc/terms/description&#34;]">
      <description>
        <xsl:apply-templates select="sp:binding[@name=$obj]/sp:literal"/>
      </description>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://purl.org/dc/terms/accessRights&#34;]">
      <access_rights>
        <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1747685414671-e5e1-7f82-b427">
          <xsl:with-param name="id">
            <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
          </xsl:with-param>
        </xsl:call-template>
      </access_rights>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://www.w3.org/ns/dcat#contactPoint&#34;]">
      <has_contact>
        <xsl:choose>
          <xsl:when test="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(current()/sp:binding[@name=$obj]/*)] and sp:binding[@name=$pred]/sp:uri/text()=$type and sp:binding[@name=$obj]/sp:uri/text()=&#34;http://xmlns.com/foaf/0.1/Agent&#34;]">
            <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806334636-9353-d66e-89dc">
              <xsl:with-param name="id">
                <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
              </xsl:with-param>
              <xsl:with-param name="type_name" select="&#34;agent&#34;"/>
            </xsl:call-template>
          </xsl:when>
          <xsl:when test="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(current()/sp:binding[@name=$obj]/*)] and sp:binding[@name=$pred]/sp:uri/text()=$type and sp:binding[@name=$obj]/sp:uri/text()=&#34;http://www.w3.org/ns/prov#Organization&#34;]">
            <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806345521-602d-5078-a2c5">
              <xsl:with-param name="id">
                <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
              </xsl:with-param>
              <xsl:with-param name="type_name" select="&#34;organization&#34;"/>
            </xsl:call-template>
          </xsl:when>
          <xsl:when test="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(current()/sp:binding[@name=$obj]/*)] and sp:binding[@name=$pred]/sp:uri/text()=$type and sp:binding[@name=$obj]/sp:uri/text()=&#34;http://www.w3.org/ns/prov#Person&#34;]">
            <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1744806350501-735b-f599-9019">
              <xsl:with-param name="id">
                <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
              </xsl:with-param>
              <xsl:with-param name="type_name" select="&#34;person&#34;"/>
            </xsl:call-template>
          </xsl:when>
        </xsl:choose>
      </has_contact>
    </xsl:for-each>
    <xsl:for-each select="//sp:result[sp:binding[@name=$subj]/*[$id_test = c:id-key(.)] and sp:binding[@name=$pred]/sp:uri/text()=&#34;http://purl.org/dc/terms/license&#34;]">
      <license>
        <xsl:call-template name="_https_003a_002f_002fofn.gov.cz_002fclass_002f1747640270910-1022-e495-9645">
          <xsl:with-param name="id">
            <xsl:copy-of select="sp:binding[@name=$obj]/*"/>
          </xsl:with-param>
        </xsl:call-template>
      </license>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="@*|*"/>
</xsl:stylesheet>
