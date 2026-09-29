#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

from __future__ import annotations

from rdflib import RDF, RDFS, SKOS, Graph, Literal, URIRef

from ccmm_invenio.fixtures.compiler.constants import (
    DATACITE_CONTRIBUTOR_TYPE_NAMESPACE,
    NOTATION_ID_DATATYPE,
    PROPS_NAMESPACE,
    make_vocabulary_namespace,
)
from ccmm_invenio.fixtures.compiler.readers import (
    CCMMRolesReader,
    RDMRolesReader,
    RolesMerger,
)

CCMM = "https://vocabs.ccmm.cz/registry/codelist/AgentRole/"
CONTRIBUTOR = CCMM + "Contributor"

DATA_MANAGER_DEFINITION = (
    "Person (or organisation with a staff of data managers, such as a data "
    "centre) responsible for maintaining the finished resource."
)

TOP_ROLES = (
    ("Creator", "Creator", "Autor"),
    ("Contributor", "Contributor", "Přispěvatel"),
    ("Publisher", "Publisher", "Vydavatel"),
)

CONTRIBUTOR_TYPES = (
    ("ContactPerson", "Contact Person", "Kontaktní osoba"),
    ("DataCollector", "Data Collector", "Sběratel dat"),
    ("DataCurator", "Data Curator", "Kurátor dat"),
    ("DataManager", "Data Manager", "Správce dat"),
    ("Distributor", "Distributor", "Distributor"),
    ("Editor", "Editor", "Editor"),
    ("HostingInstitution", "Hosting Institution", "Hostující instituce"),
    ("Producer", "Producer", "Producent"),
    ("ProjectLeader", "Project Leader", "Vedoucí projektu"),
    ("ProjectManager", "Project Manager", "Projektový manažer"),
    ("ProjectMember", "Project Member", "Člen projektového týmu"),
    ("RegistrationAgency", "Registration Agency", "Registrační agentura"),
    ("RegistrationAuthority", "Registration Authority", "Registrační autorita"),
    ("RelatedPerson", "Related Person", "Související osoba"),
    ("Researcher", "Researcher", "Výzkumník"),
    ("ResearchGroup", "Research Group", "Výzkumná skupina"),
    ("RightsHolder", "Rights Holder", "Majitel práv"),
    ("Sponsor", "Sponsor", "Sponzor"),
    ("Supervisor", "Supervisor", "Supervizor"),
    ("Translator", "Translator", "Překladatel"),
    ("WorkPackageLeader", "Work Package Leader", "Vedoucí pracovního balíku"),
    ("Other", "Other", "Jiná role"),
)


def test_load_roles():
    reader = RDMRolesReader("uri:does_not_matter")
    roles = reader.read()

    assert isinstance(roles, Graph)

    vocab = make_vocabulary_namespace("roles")

    # the well-known contact person role, carrying its DataCite
    # contributorType and MARC 21 relator code
    contactperson = vocab["contactperson"]
    assert (contactperson, RDF.type, SKOS.Concept) in roles
    assert (contactperson, SKOS.inScheme, URIRef(vocab)) in roles
    assert [str(n) for n in roles.objects(contactperson, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "contactperson"
    ]
    assert (contactperson, SKOS.prefLabel, Literal("Contact person", lang="en")) in roles
    assert (contactperson, SKOS.prefLabel, Literal("Kontaktní osoba", lang="cs")) in roles

    assert (contactperson, PROPS_NAMESPACE.datacite, Literal("ContactPerson")) in roles
    assert (contactperson, PROPS_NAMESPACE.marc, Literal("prc")) in roles

    # the concept is matched to the DataCite contributorType it maps to
    assert (
        contactperson,
        SKOS.exactMatch,
        DATACITE_CONTRIBUTOR_TYPE_NAMESPACE["ContactPerson"],
    ) in roles
    assert (
        vocab["workpackageleader"],
        SKOS.exactMatch,
        DATACITE_CONTRIBUTOR_TYPE_NAMESPACE["WorkPackageLeader"],
    ) in roles

    # the vocabulary is flat: every entry is a top concept
    concepts = set(roles.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(roles.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert not list(roles.triples((None, SKOS.broader, None)))
    assert len(concepts) == 22

    # the props are declared in the graph itself
    assert (PROPS_NAMESPACE.datacite, RDF.type, RDF.Property) in roles
    assert (PROPS_NAMESPACE.datacite, RDFS.comment, None) in roles
    assert (PROPS_NAMESPACE.marc, RDF.type, RDF.Property) in roles
    assert (PROPS_NAMESPACE.marc, RDFS.comment, None) in roles


def make_ccmm_source_graphs():
    """Mock the Skosmos data endpoint responses of the AgentRole codelist.

    The codelist URI serves the scheme and the top concepts only, the
    Contributor top concept serves its whole subtree, and each concept
    serves its own details (the definitions live only there).
    """
    scheme = Graph()
    scheme.add((URIRef(CCMM), RDF.type, SKOS.ConceptScheme))
    for name, en, cs in TOP_ROLES:
        top = URIRef(CCMM + name)
        scheme.add((URIRef(CCMM), SKOS.hasTopConcept, top))
        scheme.add((top, RDF.type, SKOS.Concept))
        scheme.add((top, SKOS.prefLabel, Literal(en, lang="en")))
        scheme.add((top, SKOS.prefLabel, Literal(cs, lang="cs")))

    # the data served for the Contributor top concept: its own details
    # and the whole subtree of its narrower concepts
    subtree = Graph()
    subtree.add((URIRef(CONTRIBUTOR), RDF.type, SKOS.Concept))
    subtree.add((URIRef(CONTRIBUTOR), SKOS.prefLabel, Literal("Contributor", lang="en")))
    subtree.add((URIRef(CONTRIBUTOR), SKOS.prefLabel, Literal("Přispěvatel", lang="cs")))
    for name, en, cs in CONTRIBUTOR_TYPES:
        child = URIRef(CONTRIBUTOR + "/" + name)
        subtree.add((child, RDF.type, SKOS.Concept))
        subtree.add((child, SKOS.prefLabel, Literal(en, lang="en")))
        subtree.add((child, SKOS.prefLabel, Literal(cs, lang="cs")))
        subtree.add((child, SKOS.broader, URIRef(CONTRIBUTOR)))

    graphs = {CCMM: scheme, CONTRIBUTOR: subtree}
    for name, en, cs in TOP_ROLES:
        if name == "Contributor":
            continue
        graph = Graph()
        concept = URIRef(CCMM + name)
        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.prefLabel, Literal(en, lang="en")))
        graph.add((concept, SKOS.prefLabel, Literal(cs, lang="cs")))
        graphs[str(concept)] = graph
    for name, en, cs in CONTRIBUTOR_TYPES:
        graph = Graph()
        concept = URIRef(CONTRIBUTOR + "/" + name)
        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.prefLabel, Literal(en, lang="en")))
        graph.add((concept, SKOS.prefLabel, Literal(cs, lang="cs")))
        if name == "DataManager":
            graph.add((concept, SKOS.definition, Literal(DATA_MANAGER_DEFINITION, lang="en")))
        graphs[str(concept)] = graph
    return graphs


def patch_agent_role(monkeypatch):
    """Serve the mocked AgentRole data endpoint responses to the reader."""
    graphs = make_ccmm_source_graphs()
    monkeypatch.setattr(CCMMRolesReader, "fetch_graph", lambda _self, url: graphs[url])
    monkeypatch.setattr(
        CCMMRolesReader,
        "data_url",
        lambda self, uri=None: self.uri if uri is None else uri,
    )


def test_data_url():
    reader = CCMMRolesReader(CCMM)

    # the vocabulary id is the segment after "codelist" - also for the
    # concept URIs nested below the top concepts
    assert reader.data_url() == (
        "https://vocabs.ccmm.cz/rest/v1/AgentRole/data"
        "?uri=https%3A%2F%2Fvocabs.ccmm.cz%2Fregistry%2Fcodelist%2FAgentRole%2F"
        "&format=text/turtle"
    )
    assert reader.data_url(CONTRIBUTOR + "/DataManager") == (
        "https://vocabs.ccmm.cz/rest/v1/AgentRole/data"
        "?uri=https%3A%2F%2Fvocabs.ccmm.cz%2Fregistry%2Fcodelist%2FAgentRole"
        "%2FContributor%2FDataManager&format=text/turtle"
    )


def test_ccmm_roles(monkeypatch):
    patch_agent_role(monkeypatch)

    reader = CCMMRolesReader(CCMM)
    graph = reader.read()

    vocab = make_vocabulary_namespace("roles")

    # the nested CCMM names become the lowercase RDM ids
    datamanager = vocab["datamanager"]
    assert (datamanager, RDF.type, SKOS.Concept) in graph
    assert (datamanager, SKOS.inScheme, URIRef(vocab)) in graph
    assert [str(n) for n in graph.objects(datamanager, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == [
        "datamanager"
    ]

    # linked to the CCMM authority, labels kept with their languages
    assert (datamanager, SKOS.exactMatch, URIRef(CONTRIBUTOR + "/DataManager")) in graph
    assert (datamanager, SKOS.prefLabel, Literal("Data Manager", lang="en")) in graph
    assert (datamanager, SKOS.prefLabel, Literal("Správce dat", lang="cs")) in graph

    # the nested concept was fetched individually - its definition, served
    # only by its own data, is present
    assert (datamanager, SKOS.definition, Literal(DATA_MANAGER_DEFINITION, lang="en")) in graph

    # the CCMM hierarchy is dropped - the concepts are flattened
    assert not list(graph.triples((None, SKOS.broader, None)))
    assert not list(graph.triples((None, SKOS.narrower, None)))

    # three general agent roles and the twenty-two contributor types
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    assert concepts == set(graph.subjects(SKOS.topConceptOf, URIRef(vocab)))
    assert {str(c).rsplit("/", 1)[-1] for c in concepts} == (
        {"creator", "contributor", "publisher"} | {name.lower() for name, _, _ in CONTRIBUTOR_TYPES}
    )


def test_roles_merger(monkeypatch):
    patch_agent_role(monkeypatch)

    rdm = RDMRolesReader().read()
    ccmm = CCMMRolesReader(CCMM).read()
    merged = RolesMerger(ccmm, rdm).merge()

    vocab = make_vocabulary_namespace("roles")
    projectmanager = vocab["projectmanager"]

    # the CCMM labels are single-valued per language - they replace the RDM
    # ones, so there is exactly one prefLabel per language
    assert (projectmanager, SKOS.prefLabel, Literal("Project Manager", lang="en")) in merged
    assert (projectmanager, SKOS.prefLabel, Literal("Projektový manažer", lang="cs")) in merged
    assert (projectmanager, SKOS.prefLabel, Literal("Manažer projektu", lang="cs")) not in merged

    # the labels of unsupported languages are discarded when reading, so they
    # do not reach the merge at all
    assert (projectmanager, SKOS.prefLabel, Literal("ProjektmanagerIn", lang="de")) not in merged

    # the definitions and both authority links are added, the props survive
    datamanager = vocab["datamanager"]
    assert (datamanager, SKOS.definition, Literal(DATA_MANAGER_DEFINITION, lang="en")) in merged
    assert (
        datamanager,
        SKOS.exactMatch,
        DATACITE_CONTRIBUTOR_TYPE_NAMESPACE["DataManager"],
    ) in merged
    assert (datamanager, SKOS.exactMatch, URIRef(CONTRIBUTOR + "/DataManager")) in merged
    assert (datamanager, PROPS_NAMESPACE.datacite, Literal("DataManager")) in merged
    assert (datamanager, PROPS_NAMESPACE.marc, Literal("dtm")) in merged

    # the id notation is not duplicated
    assert len(list(merged.objects(datamanager, SKOS.notation))) == 1


def test_roles_merger_add_missing(monkeypatch):
    patch_agent_role(monkeypatch)

    rdm = RDMRolesReader().read()
    ccmm = CCMMRolesReader(CCMM).read()

    # the general agent roles have no RDM counterpart - they are skipped
    merged = RolesMerger(ccmm, rdm).merge()
    creator = make_vocabulary_namespace("roles")["creator"]
    assert (creator, None, None) not in merged

    # ... and created complete with add_missing=True
    merged = RolesMerger(ccmm, rdm).merge(add_missing=True)
    assert (creator, RDF.type, SKOS.Concept) in merged
    assert [str(n) for n in merged.objects(creator, SKOS.notation) if n.datatype == NOTATION_ID_DATATYPE] == ["creator"]
    assert (creator, SKOS.prefLabel, Literal("Creator", lang="en")) in merged
    assert (creator, SKOS.prefLabel, Literal("Autor", lang="cs")) in merged
    assert (creator, SKOS.exactMatch, URIRef(CCMM + "Creator")) in merged
