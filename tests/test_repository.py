# SPDX-FileCopyrightText: 2025-2026 CESNET z.s.p.o
# SPDX-License-Identifier: MIT

from __future__ import annotations

from tests.model import ccmm_dataset


def test_create(app, db, identity_simple, search_clear, location, vocab_fixtures):
    service = ccmm_dataset.proxies.current_service

    rec = service.create(
        identity_simple,
        data={
            "metadata": {
                "title": "test",
                "publication_date": "2022-01-01",
                "resource_type": {"id": "dataset"},
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
