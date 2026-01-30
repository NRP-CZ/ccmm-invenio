#!/usr/bin/env bash

#
# Clone a CCMM XML version into this directory
#

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <version> <ccmm-branch>" >&2
    exit 1
fi

version="$1"
ccmm_branch="$2"
current_date=$(date +%Y-%m-%d)

dirname="ccmm-xml-releases/ccmm-$version-$current_date"

git clone --branch "$ccmm_branch" --depth 1 "https://github.com/techlib/ccmm.git" "$dirname"
rm -rf "$dirname/.git"
echo "CCMM version $version cloned into $dirname"

if [ -d .venv ] ; then rm -rf .venv ; fi
uv venv .venv
uv sync
uv pip install -e .
source .venv/bin/activate

echo "Cleaning up sources..."
python src/ccmm_versions/clean_all.py $dirname/ $dirname/out
python src/ccmm_versions/merge_schemas.py $dirname/ merged/$version-$current_date.xsd

cp merged/$version-$current_date.xsd ../src/ccmm_invenio/schemas/ccmm-$version-$current_date.xsd

echo "Getting previous version..."
previous_version_dir=$(python src/ccmm_versions/get_previous_version.py ccmm-xml-releases $dirname)
previous_version=$(echo "$previous_version_dir" | sed 's/ccmm-//')
echo "Previous version: $previous_version (at $previous_version_dir)"

echo "Generating diff between $previous_version and $version-$current_date ..."
python src/ccmm_versions/diff_ccmm.py \
    ccmm-xml-releases/$previous_version_dir/out \
    $dirname/out  \
    diffs/$previous_version--$version-$current_date.xml 

echo "Generating schema overview ..."
python src/ccmm_versions/create_schema_overview.py \
    $dirname/out \
    summaries/ccmm-$version-$current_date.summary.md

ls $dirname/metadata-samples/xml/ | while read; do

xmllint --noout \
    --schema merged/$version-$current_date.xsd \
    $dirname/metadata-samples/xml/$REPLY || echo "Validation failed"
done