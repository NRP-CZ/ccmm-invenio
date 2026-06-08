import {
  collectExistingDois,
  extractDois,
  extractYear,
  formatCreator,
  formatCreators,
  safeDecodeURI,
  splitConcatenatedUrls,
} from "./utils";

// ---------------------------------------------------------------------------
// DOI extraction
// ---------------------------------------------------------------------------

describe("safeDecodeURI", () => {
  it("decodes valid URL-encoded sequences", () => {
    expect(safeDecodeURI("hello%20world")).toBe("hello world");
    expect(safeDecodeURI("a%2Cb")).toBe("a,b");
  });

  it("returns the original string when the sequence is malformed", () => {
    // %ZZ is invalid -> decodeURIComponent throws -> we fall back to input.
    expect(safeDecodeURI("oops%ZZ")).toBe("oops%ZZ");
  });

  it("returns empty string for empty input", () => {
    expect(safeDecodeURI("")).toBe("");
  });
});

describe("splitConcatenatedUrls", () => {
  it("inserts a newline before an inline http(s) URL when one is concatenated", () => {
    const input = "https://doi.org/10.1111/ahttps://doi.org/10.2222/b";
    expect(splitConcatenatedUrls(input)).toBe(
      "https://doi.org/10.1111/a\nhttps://doi.org/10.2222/b"
    );
  });

  it("does not touch a leading http(s) URL", () => {
    const input = "https://doi.org/10.1111/a";
    expect(splitConcatenatedUrls(input)).toBe(input);
  });

  it("inserts only between non-whitespace and a URL — doesn't touch already-separated URLs", () => {
    const input = "https://doi.org/10.1111/a https://doi.org/10.2222/b";
    expect(splitConcatenatedUrls(input)).toBe(input);
  });

  it("handles three concatenated URLs", () => {
    const input =
      "https://doi.org/10.1111/ahttps://doi.org/10.2222/bhttps://doi.org/10.3333/c";
    expect(splitConcatenatedUrls(input)).toBe(
      "https://doi.org/10.1111/a\nhttps://doi.org/10.2222/b\nhttps://doi.org/10.3333/c"
    );
  });

  it("works with http:// not just https://", () => {
    expect(
      splitConcatenatedUrls("http://doi.org/10.1111/ahttp://doi.org/10.2222/b")
    ).toBe("http://doi.org/10.1111/a\nhttp://doi.org/10.2222/b");
  });
});

describe("extractDois", () => {
  it("returns empty array for empty / nullish input", () => {
    expect(extractDois("")).toEqual([]);
    expect(extractDois(null)).toEqual([]);
    expect(extractDois(undefined)).toEqual([]);
  });

  it("extracts a bare DOI", () => {
    expect(extractDois("10.1234/abcd")).toEqual([
      "https://doi.org/10.1234/abcd",
    ]);
  });

  it("extracts a full https://doi.org URL", () => {
    expect(extractDois("https://doi.org/10.1234/abcd")).toEqual([
      "https://doi.org/10.1234/abcd",
    ]);
  });

  it("extracts from the `doi:` prefix form", () => {
    expect(extractDois("doi:10.1234/abcd")).toEqual([
      "https://doi.org/10.1234/abcd",
    ]);
  });

  it("strips trailing brackets/parens but keeps DOI suffix", () => {
    expect(extractDois("[10.1234/abcd]")).toEqual([
      "https://doi.org/10.1234/abcd",
    ]);
    expect(extractDois("(10.1234/abcd)")).toEqual([
      "https://doi.org/10.1234/abcd",
    ]);
  });

  it("splits two DOIs separated by comma + space", () => {
    expect(
      extractDois("https://doi.org/10.1111/a, https://doi.org/10.2222/b")
    ).toEqual(["https://doi.org/10.1111/a", "https://doi.org/10.2222/b"]);
  });

  it("splits two DOIs separated by URL-encoded space (%20)", () => {
    expect(
      extractDois("https://doi.org/10.1111/a,%20https://doi.org/10.2222/b")
    ).toEqual(["https://doi.org/10.1111/a", "https://doi.org/10.2222/b"]);
  });

  it("splits concatenated URLs with no separator", () => {
    expect(
      extractDois("https://doi.org/10.1111/ahttps://doi.org/10.2222/b")
    ).toEqual(["https://doi.org/10.1111/a", "https://doi.org/10.2222/b"]);
  });

  it("deduplicates the same DOI appearing twice", () => {
    expect(
      extractDois("https://doi.org/10.1111/a, https://doi.org/10.1111/a")
    ).toEqual(["https://doi.org/10.1111/a"]);
  });

  it("lowercases the DOI so case-only variants collapse to one entry", () => {
    expect(
      extractDois("https://doi.org/10.1234/AbC, https://doi.org/10.1234/abc")
    ).toEqual(["https://doi.org/10.1234/abc"]);
  });

  it("preserves insertion order when deduplicating", () => {
    expect(extractDois("10.2222/b, 10.1111/a, 10.2222/b, 10.3333/c")).toEqual([
      "https://doi.org/10.2222/b",
      "https://doi.org/10.1111/a",
      "https://doi.org/10.3333/c",
    ]);
  });

  it("returns empty array for pure gibberish", () => {
    expect(extractDois("hello world this is not a doi")).toEqual([]);
    expect(extractDois("12345")).toEqual([]);
  });

  it("ignores text around DOIs in citation-like input", () => {
    const raw =
      "Smith, J. (2020). My paper. doi:10.4204/test.342. See also [10.7717/peerj.9999].";
    expect(extractDois(raw)).toEqual([
      "https://doi.org/10.4204/test.342",
      "https://doi.org/10.7717/peerj.9999",
    ]);
  });

  it("accepts DOI prefix of varying registrant length (4–9 digits)", () => {
    expect(extractDois("10.1/a")).toEqual([]); // too short (1 digit)
    expect(extractDois("10.1234/a")).toEqual(["https://doi.org/10.1234/a"]);
    expect(extractDois("10.123456789/a")).toEqual([
      "https://doi.org/10.123456789/a",
    ]);
  });
});

describe("collectExistingDois", () => {
  it("returns an empty Set for empty/nullish input", () => {
    expect(collectExistingDois(undefined)).toEqual(new Set());
    expect(collectExistingDois(null)).toEqual(new Set());
    expect(collectExistingDois([])).toEqual(new Set());
  });

  it("collects the `imported_from` URL from each resource", () => {
    const resources = [
      { imported_from: "https://doi.org/10.1111/a" },
      { imported_from: "https://doi.org/10.2222/b" },
    ];
    expect([...collectExistingDois(resources)]).toEqual([
      "https://doi.org/10.1111/a",
      "https://doi.org/10.2222/b",
    ]);
  });

  it("collects DOI identifiers (scheme: doi) and ignores other schemes", () => {
    const resources = [
      {
        identifiers: [
          { scheme: "doi", identifier: "https://doi.org/10.1111/a" },
          { scheme: "issn", identifier: "1234-5678" },
        ],
      },
    ];
    expect([...collectExistingDois(resources)]).toEqual([
      "https://doi.org/10.1111/a",
    ]);
  });

  it("normalizes a bare DOI identifier to the canonical URL form", () => {
    const resources = [
      {
        identifiers: [{ scheme: "doi", identifier: "10.1234/abcd" }],
      },
    ];
    expect([...collectExistingDois(resources)]).toEqual([
      "https://doi.org/10.1234/abcd",
    ]);
  });

  it("keeps an already-URL DOI identifier as-is", () => {
    const resources = [
      {
        identifiers: [
          { scheme: "doi", identifier: "https://doi.org/10.1111/a" },
        ],
      },
    ];
    expect([...collectExistingDois(resources)]).toEqual([
      "https://doi.org/10.1111/a",
    ]);
  });

  it("collects from both `imported_from` and `identifiers` and deduplicates", () => {
    const resources = [
      {
        imported_from: "https://doi.org/10.1111/a",
        identifiers: [{ scheme: "doi", identifier: "10.1111/a" }],
      },
    ];
    expect([...collectExistingDois(resources)]).toEqual([
      "https://doi.org/10.1111/a",
    ]);
  });

  it("skips resources without `imported_from` and without DOI identifiers", () => {
    const resources = [
      { title: "Manual entry, no DOI" },
      { identifiers: [] },
      { identifiers: [{ scheme: "issn", identifier: "1234-5678" }] },
    ];
    expect([...collectExistingDois(resources)]).toEqual([]);
  });

  it("deduplicates the same DOI stored under http://, https://, and dx.doi.org variants", () => {
    const resources = [
      { imported_from: "http://doi.org/10.1234/abcd" },
      {
        identifiers: [
          { scheme: "doi", identifier: "https://dx.doi.org/10.1234/abcd" },
        ],
      },
      { imported_from: "https://doi.org/10.1234/abcd" },
    ];
    expect([...collectExistingDois(resources)]).toEqual([
      "https://doi.org/10.1234/abcd",
    ]);
  });

  it("lowercases collected DOIs so case-only variants match extractDois output", () => {
    const resources = [
      { imported_from: "https://doi.org/10.1234/AbC" },
      { identifiers: [{ scheme: "doi", identifier: "10.5678/DeF" }] },
    ];
    expect([...collectExistingDois(resources)]).toEqual([
      "https://doi.org/10.1234/abc",
      "https://doi.org/10.5678/def",
    ]);
  });

  it("skips identifier entries with missing identifier or scheme", () => {
    const resources = [
      {
        identifiers: [
          { scheme: "doi" }, // no identifier
          { identifier: "10.1111/a" }, // no scheme
          null,
        ],
      },
    ];
    expect([...collectExistingDois(resources)]).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Citation formatting
// ---------------------------------------------------------------------------

const author = (family, given) => ({
  person_or_org: { family_name: family, given_name: given },
});

describe("formatCreator", () => {
  it("formats a personal author with given + family name", () => {
    expect(
      formatCreator({
        person_or_org: {
          type: "personal",
          family_name: "Aspelmeyer",
          given_name: "Markus",
          name: "Aspelmeyer, Markus",
        },
      })
    ).toBe("ASPELMEYER, M.");
  });

  it("uppercases family name even without given name", () => {
    expect(
      formatCreator({ person_or_org: { family_name: "Aspelmeyer" } })
    ).toBe("ASPELMEYER");
  });

  it("falls back to uppercased `name` when family_name is missing", () => {
    expect(
      formatCreator({ person_or_org: { name: "OpenAI Research Team" } })
    ).toBe("OPENAI RESEARCH TEAM");
  });

  it("returns null when person_or_org is missing", () => {
    expect(formatCreator({})).toBe(null);
    expect(formatCreator(null)).toBe(null);
    expect(formatCreator(undefined)).toBe(null);
  });

  it("returns null when both family_name and name are missing", () => {
    expect(formatCreator({ person_or_org: { given_name: "Markus" } })).toBe(
      null
    );
  });

  it("uppercases the given-name initial", () => {
    expect(
      formatCreator({
        person_or_org: { family_name: "Smith", given_name: "john" },
      })
    ).toBe("SMITH, J.");
  });

  it("trims whitespace around given name", () => {
    expect(
      formatCreator({
        person_or_org: { family_name: "Smith", given_name: "  john  " },
      })
    ).toBe("SMITH, J.");
  });
});

describe("formatCreators", () => {
  it("returns an empty string for empty/nullish input", () => {
    expect(formatCreators([])).toBe("");
    expect(formatCreators(null)).toBe("");
    expect(formatCreators(undefined)).toBe("");
  });

  it("returns just the family name for a single creator with no given name", () => {
    expect(formatCreators([author("Aspelmeyer")])).toBe("ASPELMEYER");
  });

  it("returns FAMILY, G. for a single creator with given name", () => {
    expect(formatCreators([author("Aspelmeyer", "Markus")])).toBe(
      "ASPELMEYER, M."
    );
  });

  it("joins two creators with `and`", () => {
    expect(
      formatCreators([author("Smith", "John"), author("Doe", "Jane")])
    ).toBe("SMITH, J. and DOE, J.");
  });

  it("joins three creators with comma + `and` before the last", () => {
    expect(
      formatCreators([
        author("Smith", "John"),
        author("Doe", "Jane"),
        author("Roe", "Mary"),
      ])
    ).toBe("SMITH, J., DOE, J. and ROE, M.");
  });

  it("caps at 5 creators and appends ` et al.`", () => {
    const creators = ["A", "B", "C", "D", "E", "F", "G"].map((n) => author(n));
    expect(formatCreators(creators)).toBe("A, B, C, D and E et al.");
  });

  it("includes all 5 when there are exactly 5 creators (no et al.)", () => {
    const creators = ["A", "B", "C", "D", "E"].map((n) => author(n));
    expect(formatCreators(creators)).toBe("A, B, C, D and E");
  });

  it("filters out creators that can't be formatted (no name)", () => {
    expect(
      formatCreators([
        author("Smith", "John"),
        { person_or_org: { given_name: "OnlyGiven" } }, // no family/name -> null
        author("Doe", "Jane"),
      ])
    ).toBe("SMITH, J. and DOE, J.");
  });

  it("returns empty string when all creators are unformattable", () => {
    expect(formatCreators([{ person_or_org: {} }, {}])).toBe("");
  });
});

describe("extractYear", () => {
  it("extracts a 4-digit year from a YYYY-MM-DD string", () => {
    expect(extractYear("2023-05-19")).toBe("2023");
  });

  it("extracts a 4-digit year from a YYYY string", () => {
    expect(extractYear("2024")).toBe("2024");
  });

  it("returns empty string when no year prefix is present", () => {
    expect(extractYear("not a date")).toBe("");
    expect(extractYear("19/05/2023")).toBe("");
  });

  it("returns empty string for empty/nullish input", () => {
    expect(extractYear("")).toBe("");
    expect(extractYear(null)).toBe("");
    expect(extractYear(undefined)).toBe("");
  });

  it("coerces non-string input via String()", () => {
    expect(extractYear(2023)).toBe("2023");
  });
});
