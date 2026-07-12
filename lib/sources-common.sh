# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
# shellcheck shell=sh

# Shared helper for generating apt .sources stanzas, sourced by
# generate-sources-tar (which writes them to files for artifact upload) and
# generate-step-summary (which embeds them in the human-facing summary). Keeping
# a single implementation ensures the machine-readable artifacts and the
# instructions shown to users never drift apart.

# Inputs (from the environment):
#   DEBUSINE_HOST
#   DEBUSINE_SCOPE
#   DEBUSINE_USER
#   DEBUSINE_TOKEN
#   SUITE

# emit_sources WORKSPACE
# Prints an apt deb822 .sources stanza for the given Debusine workspace to
# stdout, embedding that workspace's signing key.
emit_sources() {
	_workspace="$1"
	_uri="https://deb.${DEBUSINE_HOST}/${DEBUSINE_SCOPE}/${_workspace}/"
	_public_key=$(curl -fsSu "${DEBUSINE_USER}:${DEBUSINE_TOKEN}" "${_uri}signing-keys.asc"|sed -e 's/^$/./;s/^/ /')
	cat <<END
Types: deb deb-src
URIs: ${_uri}
Suites: ${SUITE}
Components: main contrib non-free non-free-firmware
Signed-By:
${_public_key}
END
}
