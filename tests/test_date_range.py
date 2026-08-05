from copy import deepcopy

from ccmm_invenio.search.date_ranges import CCMMDateRangesDumperExt


def test_dumps_dates_and_related_resource_dates_to_date_ranges():
    data = {
        "metadata": {
            "dates": [{"date": "2020-05-10"}],
            "related_resources": [
                {
                    "title": {"en": "Related dataset"},
                    "dates": [
                        {"date": "2020/2021"},
                        {"date": "2024-02"},
                    ],
                },
            ],
        },
    }

    result = CCMMDateRangesDumperExt().dump(None, deepcopy(data))

    assert result["metadata"]["dates"][0]["date"] == {
        "gte": "2020-05-10",
        "lte": "2020-05-10",
    }
    assert result["metadata"]["related_resources"][0]["dates"][0]["date"] == {
        "gte": "2020-01-01",
        "lte": "2021-12-31",
    }
    assert result["metadata"]["related_resources"][0]["dates"][1]["date"] == {
        "gte": "2024-02-01",
        "lte": "2024-02-29",
    }