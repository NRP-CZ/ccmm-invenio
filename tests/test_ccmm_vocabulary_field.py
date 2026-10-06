#
# Copyright (c) 2026 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

import pytest
from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as vocab_service
from marshmallow import ValidationError

from ccmm_invenio.resources.serializers.ccmm.converter import (
    NS_CCMM_1_1_0,
    XMLToGenericJSONConverter,
    ccmm_1_1_0_schema,
)
from ccmm_invenio.resources.serializers.ccmm.schema.vocabs import CCMMVocabularyField

COAR = "http://purl.org/coar/access_right/"


@pytest.fixture(scope="module")
def access_rights(app, database, search):
    vocab_service.create_type(system_identity, "accessrights", "ar")
    for entry in [
        {
            "id": "open",
            "title": {"cs": "otevřený přístup", "en": "open access"},
            "mappings": [
                {"identifier": f"{COAR}c_abf2", "scheme": COAR, "relation": "exactMatch"},
                {
                    "identifier": "http://example.org/open-broad",
                    "scheme": "http://example.org/",
                    "relation": "broadMatch",
                },
                {
                    "identifier": "http://example.org/open-narrow",
                    "scheme": "http://example.org/",
                    "relation": "narrowMatch",
                },
            ],
        },
        {
            "id": "embargoed",
            "title": {"en": "embargoed access"},
            "mappings": [
                {"identifier": "http://example.org/embargo", "scheme": "http://example.org/", "relation": "broadMatch"},
            ],
        },
        {"id": "unmapped", "title": {"en": "no mappings"}},
    ]:
        vocab_service.create(system_identity, {"type": "accessrights", **entry})
    vocab_service.indexer.refresh()
    return CCMMVocabularyField("accessrights")


def test_serialize(access_rights):
    field = access_rights
    # exactMatch wins over broadMatch, title becomes the label
    open_access = field.serialize("v", {"v": {"id": "open"}})
    assert open_access == {
        "iri": f"{COAR}c_abf2",
        "label": [{"lang": "cs", "$": "otevřený přístup"}, {"lang": "en", "$": "open access"}],
    }
    # broadMatch is used when there is no exactMatch
    assert field.serialize("v", {"v": {"id": "embargoed"}})["iri"] == "http://example.org/embargo"
    # no usable mapping - link to the vocabulary item
    assert field.serialize("v", {"v": {"id": "unmapped"}})["iri"].endswith("/vocabularies/accessrights/unmapped")
    assert field.serialize("v", {"v": None}) is None

    # the serialized value is a valid ccmm vocabulary element
    _xml, errors = XMLToGenericJSONConverter().json_to_xml(
        ccmm_1_1_0_schema, open_access, f"{{{NS_CCMM_1_1_0}}}access_rights"
    )
    assert errors == []


def test_deserialize(access_rights):
    field = access_rights
    assert field.deserialize({"iri": f"{COAR}c_abf2"}) == {"id": "open"}
    assert field.deserialize(f"{COAR}c_abf2") == {"id": "open"}
    # narrowMatch is usable for import
    assert field.deserialize({"iri": "http://example.org/open-narrow"}) == {"id": "open"}
    # broadMatch is not usable for import
    with pytest.raises(ValidationError):
        field.deserialize({"iri": "http://example.org/embargo"})
    with pytest.raises(ValidationError):
        field.deserialize({"iri": "http://example.org/unknown"})
    with pytest.raises(ValidationError):
        field.deserialize({})
