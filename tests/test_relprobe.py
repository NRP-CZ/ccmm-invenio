"""Temp probe: list relation fields of the built model's record class."""

import json

from tests.model import ccmm_dataset
from tests.test_ccmm_import_http import vocabularies  # noqa: F401


def test_probe(app, db, location, vocabularies):  # noqa: F811
    service = ccmm_dataset.proxies.current_service
    rc = service.record_cls
    out = {"record_cls": rc.__name__}
    rels = getattr(rc, "relations", None)
    out["relations_type"] = type(rels).__name__
    fields_map = {}
    if rels is not None:
        fm = getattr(rels, "fields", None) or getattr(rels, "_fields", None)
        if isinstance(fm, dict):
            fields_map = fm
        else:
            for name in dir(rels):
                if name.startswith("_"):
                    continue
                v = getattr(rels, name)
                if "Relation" in type(v).__name__:
                    fields_map[name] = v
    out["relation_fields"] = {k: type(v).__name__ for k, v in fields_map.items()}
    with open("/tmp/relations_probe.json", "w") as fp:
        json.dump(out, fp, indent=2)
