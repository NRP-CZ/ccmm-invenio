import { i18next } from "@translations/ccmm_invenio";

// ---------------------------------------------------------------------------
// DOI extraction (used by LoadFromDoiModal)
// ---------------------------------------------------------------------------

/**
 * Matches a DOI in `10.<4–9 digit registrant>/<suffix>` form. The suffix
 * character class intentionally excludes whitespace and common list
 * separators (`,`, `;`, quotes, angle brackets) so DOI lists don't get
 * over-eaten by greedy matching.
 *
 * @type {RegExp}
 */
export const DOI_RE = /\b(10\.\d{4,9}\/[^\s,;"'<>]+)\b/gi;

/**
 * Hard cap on how many DOIs the Load-from-DOI modal will process per batch.
 * Keeps both client-side and upstream load bounded.
 *
 * @type {number}
 */
export const MAX_DOIS_PER_BATCH = 20;

/**
 * Run {@link decodeURIComponent} safely — if the input contains a malformed
 * percent-escape sequence, return the original string instead of throwing.
 *
 * @param {string} s - Possibly URL-encoded string.
 * @returns {string} The decoded string, or the original on malformed input.
 */
export const safeDecodeURI = (s) => {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
};

/**
 * Insert a newline before any inline `http(s)://` so concatenated URLs
 * (e.g. `"https://doi.org/X/Yhttps://doi.org/A/B"`) don't get greedy-matched
 * as one giant DOI by {@link DOI_RE}'s suffix character class.
 *
 * The replacement only fires when the URL is preceded by a non-whitespace
 * character, so already-separated URLs are left untouched.
 *
 * @param {string} s - Raw input that may contain concatenated URLs.
 * @returns {string} Input with newlines inserted before inline URLs.
 */
export const splitConcatenatedUrls = (s) =>
  s.replace(/(\S)(https?:\/\/)/gi, "$1\n$2");

/**
 * Extract DOI URLs from arbitrary text and normalize each to its canonical
 * `https://doi.org/<doi>` URL form.
 *
 * Pre-processes the input by URL-decoding and splitting concatenated URLs,
 * then runs {@link DOI_RE} over the result. Returns insertion-ordered
 * deduplication via `Set`.
 *
 * Accepts bare DOIs, `doi:` prefixed DOIs, full URLs, bracketed/parenthesized
 * DOIs, and DOIs embedded in citation text.
 *
 * @param {string|null|undefined} raw - Arbitrary user input (paste, typed, etc.).
 * @returns {string[]} Unique, normalized DOI URLs in order of appearance.
 */
export const extractDois = (raw) => {
  if (!raw) return [];
  const prepared = splitConcatenatedUrls(safeDecodeURI(raw));
  // Lowercase each match before dedup — DOIs are case-insensitive per the
  // DOI Handbook, so "10.1234/Abc" and "10.1234/abc" must collapse to one.
  const matches = [...prepared.matchAll(DOI_RE)].map((m) => m[1].toLowerCase());
  return [...new Set(matches)].map((doi) => `https://doi.org/${doi}`);
};

/**
 * Build a `Set` of canonical DOI URLs already represented on the record.
 *
 * Two sources are merged:
 *   1. Each related-resource's `imported` field (set when the item came in
 *      via the Load-from-DOI modal).
 *   2. Each item's `identifiers[]` array entries whose `scheme === "doi"`.
 *      Bare-form identifiers are normalized to the `https://doi.org/...` URL.
 *
 * Used by the modal to detect duplicates before submitting.
 *
 * @param {Array<object>|null|undefined} existingResources - Current value of
 *   the related-resources field array from Formik state.
 * @returns {Set<string>} Set of canonical DOI URLs already on the record.
 */
export const collectExistingDois = (existingResources) => {
  const set = new Set();
  for (const resource of existingResources || []) {
    // Route both sources through extractDois so dedup is canonical regardless
    // of how the existing data was stored (bare DOI, http vs https,
    // doi.org vs dx.doi.org, mixed case, etc.).
    if (resource?.imported) {
      for (const url of extractDois(resource.imported)) {
        set.add(url);
      }
    }
    for (const id of resource?.identifiers || []) {
      if (id?.scheme === "doi" && id?.identifier) {
        for (const url of extractDois(id.identifier)) {
          set.add(url);
        }
      }
    }
  }
  return set;
};

// ---------------------------------------------------------------------------
// Citation formatting (used by RelatedResourceCitation)
// ---------------------------------------------------------------------------

/**
 * Maximum number of creators rendered before collapsing the rest into
 * an ` et al.` suffix.
 *
 * @type {number}
 */
export const MAX_CREATORS = 5;

/**
 * Format a single creator into ISO 690-ish citation form: uppercased family
 * name + comma + uppercased given-name initial, e.g. `"SMITH, J."`.
 *
 * Fallbacks:
 *   - If `family_name` is missing but `name` is present, return uppercased
 *     `name` (e.g. for organizational authors).
 *   - Otherwise return `null` so the caller can drop unformattable entries.
 *
 * @param {object|null|undefined} creator - A creator entry of shape
 *   `{ person_or_org: { family_name, given_name, name, ... } }`.
 * @returns {string|null} Formatted creator, or `null` if no usable name.
 */
export const formatCreator = (creator) => {
  const p = creator?.person_or_org;
  if (!p) return null;
  if (p.family_name) {
    const family = p.family_name.toUpperCase();
    const given = p.given_name?.trim();
    return given ? `${family}, ${given[0].toUpperCase()}.` : family;
  }
  if (p.name) return p.name.toUpperCase();
  return null;
};

/**
 * Format a list of creators into a citation-ready string.
 *
 * - Caps the visible list at {@link MAX_CREATORS}; appends ` et al.` if
 *   more were present in the input.
 * - Joins with `", "` between entries and the localized `"and"` before the
 *   last entry.
 * - Silently drops entries that {@link formatCreator} can't format.
 *
 * @param {Array<object>|null|undefined} creators - Creators array from the
 *   resource metadata.
 * @returns {string} Citation-ready joined string, or `""` when there's
 *   nothing usable to render.
 */
export const formatCreators = (creators) => {
  if (!creators?.length) return "";
  const formatted = creators
    .slice(0, MAX_CREATORS)
    .map(formatCreator)
    .filter(Boolean);
  if (formatted.length === 0) return "";
  let joined;
  if (formatted.length === 1) {
    joined = formatted[0];
  } else {
    const head = formatted.slice(0, -1).join(", ");
    const tail = formatted[formatted.length - 1];
    joined = `${head} ${i18next.t("and")} ${tail}`;
  }
  if (creators.length > MAX_CREATORS) joined += " et al.";
  return joined;
};

/**
 * Pull a 4-digit year from a publication-date string.
 *
 * Accepts any input whose leading 4 characters are digits — so `YYYY`,
 * `YYYY-MM`, `YYYY-MM-DD`, etc. all work. Returns `""` when nothing matches.
 *
 * @param {string|number|null|undefined} date - Publication date as it
 *   appears in resource metadata.
 * @returns {string} The 4-digit year as a string, or `""` if not extractable.
 */
export const extractYear = (date) => {
  if (!date) return "";
  const match = String(date).match(/^(\d{4})/);
  return match ? match[1] : "";
};
