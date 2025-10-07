#
# Copyright (c) 2025 CESNET z.s.p.o.
#
# This file is a part of ccmm-invenio (see https://github.com/NRP-CZ/ccmm-invenio).
#
# ccmm-invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#
from __future__ import annotations

from tests.model import production_dataset


def test_create(app, db, identity_simple, search_clear, location):
    service = production_dataset.proxies.current_service

    rec = service.create(
        identity_simple,
        data={
            "metadata": {
                "title": "test",
                "creators": [
                    {
                        "person_or_org": {
                            "type": "personal",
                            "given_name": "John",
                            "family_name": "Doe",
                        }
                    }
                ],
            }
        },
    ).to_dict()

    assert rec.get("errors", []) == []
