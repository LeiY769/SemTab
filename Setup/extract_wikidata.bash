#!/bin/bash
#SBATCH --job-name=reduce_wikidata
#SBATCH --output=logs/reduce_wikidata_%j.out
#SBATCH --error=logs/reduce_wikidata_%j.err
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=70G

set -euo pipefail

module load Java/21.0.5

BASE_DIR="${GLOBALSCRATCH}/${USER}"
NT_FILE="${BASE_DIR}/nt/wikidata2024.nt"

: "${LOCALSCRATCH:?LOCALSCRATCH not defined}"

mkdir -p "$LOCALSCRATCH/tmp"
mkdir -p logs

export TMPDIR="$LOCALSCRATCH/tmp"
export LC_ALL=C

FILTERED_NT="${LOCALSCRATCH}/dataset.nt"

ENG_DIR="${BASE_DIR}/reduced"
mkdir -p "$ENG_DIR"

echo "============================================================"
echo "        Mini Wikidata extraction for SemTab"
echo "============================================================"
echo "Source : $NT_FILE"
echo "Start  : $(date)"
echo ""


SCHEMA_NAME_URI="<http://schema.org/name>"
SCHEMA_DESC_URI="<http://schema.org/description>"

RDFS_LABEL_URI="<http://www.w3.org/2000/01/rdf-schema#label>"
ALT_LABEL_URI="<http://www.w3.org/2004/02/skos/core#altLabel>"

P31_URI="<http://www.wikidata.org/prop/direct/P31>"
P279_URI="<http://www.wikidata.org/prop/direct/P279>"

SITE_FILTER="en.wikipedia.org/wiki/"

EN_FILTER='@en'

echo "Predicates selected:"
echo "  schema:name"
echo "  schema:description"
echo "  rdfs:label"
echo "  skos:altLabel"
echo "  P31 (instance of)"
echo "  P279 (subclass of)"
echo "  Wikipedia sitelinks"
echo ""



extract() {
    local name="$1"
    local pattern="$2"
    local outfile="$3"
    local lang_filter="${4:-}"

    echo "[START] $name"

    if [[ -n "$lang_filter" ]]; then
        grep -F "$pattern" "$NT_FILE" \
            | grep "$lang_filter" \
            > "$outfile"
    else
        grep -F "$pattern" "$NT_FILE" \
            > "$outfile"
    fi

    local count
    count=$(wc -l < "$outfile")

    echo "[DONE ] $name — $count triples"
}
extract "schema:name EN" \
    "$SCHEMA_NAME_URI" \
    "${LOCALSCRATCH}/schema_name_en.nt" \
    "$EN_FILTER" &
PID1=$!

extract "schema:description EN" \
    "$SCHEMA_DESC_URI" \
    "${LOCALSCRATCH}/description_en.nt" \
    "$EN_FILTER" &
PID2=$!

extract "rdfs:label EN" \
    "$RDFS_LABEL_URI" \
    "${LOCALSCRATCH}/rdfs_label_en.nt" \
    "$EN_FILTER" &
PID3=$!

extract "altLabel EN" \
    "$ALT_LABEL_URI" \
    "${LOCALSCRATCH}/altlabel_en.nt" \
    "$EN_FILTER" &
PID4=$!

extract "P31" \
    "$P31_URI" \
    "${LOCALSCRATCH}/p31.nt" &
PID5=$!

extract "P279" \
    "$P279_URI" \
    "${LOCALSCRATCH}/p279.nt" &
PID6=$!


extract "Wikipedia sitelinks" \
    "$SITE_FILTER" \
    "${LOCALSCRATCH}/sitelinks.nt" &
PID10=$!

wait $PID1 $PID2 $PID3 $PID4 $PID5 \
     $PID6 $PID10

echo ""
echo "============================================================"
echo "Concatenation"
echo "============================================================"

cat \
    "${LOCALSCRATCH}/schema_name_en.nt" \
    "${LOCALSCRATCH}/description_en.nt" \
    "${LOCALSCRATCH}/rdfs_label_en.nt" \
    "${LOCALSCRATCH}/altlabel_en.nt" \
    "${LOCALSCRATCH}/p31.nt" \
    "${LOCALSCRATCH}/p279.nt" \
    "${LOCALSCRATCH}/sitelinks.nt" \
    > "$FILTERED_NT"

echo ""
echo "Cleaning temporary files..."

rm -f \
    "${LOCALSCRATCH}/schema_name_en.nt" \
    "${LOCALSCRATCH}/description_en.nt" \
    "${LOCALSCRATCH}/rdfs_label_en.nt" \
    "${LOCALSCRATCH}/altlabel_en.nt" \
    "${LOCALSCRATCH}/p31.nt" \
    "${LOCALSCRATCH}/p279.nt" \
    "${LOCALSCRATCH}/sitelinks.nt"

TOTAL=$(wc -l < "$FILTERED_NT")
SIZE=$(du -sh "$FILTERED_NT" | cut -f1)

echo ""
echo "============================================================"
echo "Extraction completed"
echo "============================================================"
echo "Triples : $TOTAL"
echo "Size    : $SIZE"
echo "End     : $(date)"
echo ""

FINAL_FILE="${ENG_DIR}/reduced_semtab.nt"

echo "Copying final dataset..."
cp "$FILTERED_NT" "$FINAL_FILE"

echo ""
echo "Final file:"
ls -lh "$FINAL_FILE"

echo ""
echo "Done."
