# Vocabulary Mapping

## SKOS format

Vocabularies are provided in SKOS format as turtle files. During the import process, the turtle files are loaded into the triplestore.
Mappings are provided as TSV files in the https://mapping-commons.github.io/sssom/dev/ format (https://mapping-commons.github.io/sssom/dev/spec-formats-tsv/). We recognize only:

* skos:exactMatch
* skos:broadMatch
* skos:narrowMatch

During the import process, the TSV files are parsed and the mappings are loaded into the triplestore as RDF triples with the following structure:

```turtle
@prefix EXT: <https://example.org/properties/> .
@prefix FOODON: <http://purl.obolibrary.org/obo/FOODON_> .
@prefix KF_FOOD: <https://kewl-foodie.inc/food/> .
@prefix ORCID: <https://orcid.org/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix pav: <http://purl.org/pav/> .
@prefix semapv: <https://w3id.org/semapv/vocab/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix sssom: <https://w3id.org/sssom/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://vocabs.ccmm.cz/mappings> a sssom:MappingSet;
  dcterms:description "Mappings between CCMM vocabularies and different metadata schemas";
  dcterms:license <https://creativecommons.org/licenses/by/4.0/>;
  sssom:mappings [ a owl:Axiom;
      pav:authoredBy ORCID:0000-0002-7356-1779;
      dcterms:created "2025-07-14"^^xsd:date;
      owl:annotatedProperty skos:exactMatch;
      owl:annotatedSource KF_FOOD:F001;
      owl:annotatedTarget FOODON:00002473;
      sssom:confidence 0.95;
      sssom:mapping_justification semapv:ManualMappingCuration;
      sssom:object_label "apple (whole)";
      sssom:subject_label "apple"
    ]
```
