#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────
# Debusine Action Unit Test Runner
#
# Usage:
#   ./debusine-trigger-test.sh [suite1.json suite2.json ...]
#
# Optional env vars:
#   WORKSPACE_DIR  - directory where artifact.yaml / workflowlog.yml live
#                    defaults to GITHUB_WORKSPACE, then pwd
# ─────────────────────────────────────────────

TEST_CASES_DIR="$(cd "$(dirname "$0")/test-cases" && pwd)"

# ── Resolve workspace (where action output files live) ────
WORKSPACE_DIR="${WORKSPACE_DIR:-${GITHUB_WORKSPACE:-$(pwd)}}"
echo "Workspace dir : $WORKSPACE_DIR"

# ── Resolve which test suites to run ──────────
if [ "$#" -gt 0 ]; then
  TEST_FILES=("$@")
else
  mapfile -t TEST_FILES < <(find "$TEST_CASES_DIR" -name "*.json" | sort)
fi

if [ "${#TEST_FILES[@]}" -eq 0 ]; then
  echo "::error::No test JSON files found in $TEST_CASES_DIR"
  exit 1
fi

# ── Global counters ───────────────────────────
GRAND_TOTAL=0
GRAND_PASSED=0
GRAND_FAILED=0
SUITE_SUMMARIES=()

# ── Helper: resolve env_match expected value ──
resolve_expected() {
  local raw="$1"
  if [[ "$raw" =~ ^\$[A-Z_]+$ ]]; then
    local var_name="${raw:1}"
    echo "${!var_name:-}"
  else
    echo "$raw"
  fi
}

# ─────────────────────────────────────────────
# Run a single test suite (JSON file)
# ─────────────────────────────────────────────
run_suite() {
  local TEST_CONFIG="$1"

  if [ ! -f "$TEST_CONFIG" ]; then
    echo "::error::Test configuration file not found: $TEST_CONFIG"
    return 1
  fi

  local SUITE_NAME SUITE_DESC TOTAL_TESTS
  SUITE_NAME=$(jq -r '.action // "unknown"' "$TEST_CONFIG")
  SUITE_DESC=$(jq -r '.description // ""' "$TEST_CONFIG")
  TOTAL_TESTS=$(jq '.tests | length' "$TEST_CONFIG")
  local PASSED=0 FAILED=0

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "::group::Suite: $SUITE_NAME  ($TEST_CONFIG)"
  echo "Description : $SUITE_DESC"
  echo "Test count  : $TOTAL_TESTS"
  echo "Env context : ARTIFACT_ID=${ARTIFACT_ID:-<not set>}  WORKFLOW_ID=${WORKFLOW_ID:-<not set>}"
  echo "Working dir : $WORKSPACE_DIR"
  echo ""

  for i in $(seq 0 $((TOTAL_TESTS - 1))); do
    local TEST_NAME COMMAND EXPECTED VALIDATION_TYPE DESCRIPTION
    TEST_NAME=$(jq -r ".tests[$i].name" "$TEST_CONFIG")
    COMMAND=$(jq -r ".tests[$i].command" "$TEST_CONFIG")
    EXPECTED=$(jq -r ".tests[$i].expected" "$TEST_CONFIG")
    VALIDATION_TYPE=$(jq -r ".tests[$i].validation_type" "$TEST_CONFIG")
    DESCRIPTION=$(jq -r ".tests[$i].description" "$TEST_CONFIG")

    echo "  ┌─ Test $((i + 1))/$TOTAL_TESTS: $TEST_NAME"
    echo "  │  Description : $DESCRIPTION"
    echo "  │  Command     : $COMMAND"
    echo "  │  Expect      : $EXPECTED  (type: $VALIDATION_TYPE)"

    # Execute command from WORKSPACE_DIR so relative paths resolve correctly
    local OUTPUT EXIT_CODE=0
    OUTPUT=$(cd "$WORKSPACE_DIR" && eval "$COMMAND" 2>&1) || EXIT_CODE=$?

    echo "  │  Output      : $OUTPUT"
    echo "  │  Exit code   : $EXIT_CODE"

    local RESULT="FAILED" REASON=""

    case "$VALIDATION_TYPE" in
      "regex")
        if echo "$OUTPUT" | grep -qE "$EXPECTED"; then
          RESULT="PASSED"
        else
          REASON="output did not match regex: $EXPECTED"
        fi
        ;;
      "numeric")
        if echo "$OUTPUT" | grep -qE "^[0-9]+$"; then
          RESULT="PASSED"
        else
          REASON="output is not a numeric value: $OUTPUT"
        fi
        ;;
      "exact")
        if [ "$OUTPUT" = "$EXPECTED" ]; then
          RESULT="PASSED"
        else
          REASON="expected '$EXPECTED', got '$OUTPUT'"
        fi
        ;;
      "contains")
        if echo "$OUTPUT" | grep -qF "$EXPECTED"; then
          RESULT="PASSED"
        else
          REASON="output does not contain '$EXPECTED'"
        fi
        ;;
      "env_match")
        local RESOLVED
        RESOLVED=$(resolve_expected "$EXPECTED")
        if [ -z "$RESOLVED" ]; then
          REASON="env var '$EXPECTED' is not set or empty"
        elif [ "$OUTPUT" = "$RESOLVED" ]; then
          RESULT="PASSED"
        else
          REASON="expected env value '$RESOLVED', got '$OUTPUT'"
        fi
        ;;
      "exit_code")
        if [ "$EXIT_CODE" = "$EXPECTED" ]; then
          RESULT="PASSED"
        else
          REASON="expected exit code $EXPECTED, got $EXIT_CODE"
        fi
        ;;
      *)
        REASON="unknown validation type: $VALIDATION_TYPE"
        ;;
    esac

    if [ "$RESULT" = "PASSED" ]; then
      echo "  └─ ✓ PASSED"
      PASSED=$((PASSED + 1))
    else
      echo "  └─ ✗ FAILED — $REASON"
      FAILED=$((FAILED + 1))
    fi
    echo ""
  done

  echo "::endgroup::"

  local RATE=0
  [ "$TOTAL_TESTS" -gt 0 ] && RATE=$(( PASSED * 100 / TOTAL_TESTS ))
  echo "  Suite result: $PASSED/$TOTAL_TESTS passed  ($RATE%)"
  echo ""

  GRAND_TOTAL=$((GRAND_TOTAL + TOTAL_TESTS))
  GRAND_PASSED=$((GRAND_PASSED + PASSED))
  GRAND_FAILED=$((GRAND_FAILED + FAILED))

  local STATUS_ICON="✓"
  [ "$FAILED" -gt 0 ] && STATUS_ICON="✗"
  SUITE_SUMMARIES+=("| **${SUITE_NAME}** | ${TOTAL_TESTS} | ${PASSED} | ${FAILED} | ${RATE}% | ${STATUS_ICON} |")
}

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         Debusine Action Test Runner              ║"
echo "╚══════════════════════════════════════════════════╝"
echo "Suites to run: ${#TEST_FILES[@]}"
echo ""

for suite_file in "${TEST_FILES[@]}"; do
  run_suite "$suite_file"
done

GRAND_RATE=0
[ "$GRAND_TOTAL" -gt 0 ] && GRAND_RATE=$(( GRAND_PASSED * 100 / GRAND_TOTAL ))

echo "╔══════════════════════════════════════════════════╗"
echo "║                 FINAL RESULTS                   ║"
echo "╚══════════════════════════════════════════════════╝"
echo "  Total  : $GRAND_TOTAL"
echo "  Passed : $GRAND_PASSED"
echo "  Failed : $GRAND_FAILED"
echo "  Rate   : $GRAND_RATE%"
echo ""

{
  echo "## 🧪 Debusine Action Test Results"
  echo ""
  echo "| Suite | Total | ✓ Passed | ✗ Failed | Rate | Status |"
  echo "|-------|-------|----------|----------|------|--------|"
  for row in "${SUITE_SUMMARIES[@]}"; do
    echo "$row"
  done
  echo ""
  echo "---"
  echo ""
  echo "### Overall"
  echo ""
  echo "| Metric | Value |"
  echo "|--------|-------|"
  echo "| **Total Tests** | $GRAND_TOTAL |"
  echo "| **Passed** | ✓ $GRAND_PASSED |"
  echo "| **Failed** | ✗ $GRAND_FAILED |"
  echo "| **Success Rate** | $GRAND_RATE% |"
  echo ""
  echo "**Artifact ID:** \`${ARTIFACT_ID:-N/A}\`"
  echo "**Workflow ID:** \`${WORKFLOW_ID:-N/A}\`"
  echo "**Workflow URL:** ${WORKFLOW_URL:-N/A}"
} >> "$GITHUB_STEP_SUMMARY"

if [ "$GRAND_FAILED" -eq 0 ]; then
  echo "::notice::✓ All $GRAND_PASSED tests passed across ${#TEST_FILES[@]} suite(s)"
  exit 0
else
  echo "::error::$GRAND_FAILED test(s) failed out of $GRAND_TOTAL across ${#TEST_FILES[@]} suite(s)"
  exit 1
fi
