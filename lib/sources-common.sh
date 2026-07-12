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

# emit_sources WORKSPACE [KEY_FILE]
# Prints an apt deb822 .sources stanza for the given Debusine workspace to
# stdout, embedding that workspace's signing key. The key is read from KEY_FILE
# when given, and fetched from the workspace's signing-keys.asc otherwise.
#
# Pass KEY_FILE for the ephemeral build workspace: its signing-keys.asc can
# briefly return a well-formed but empty armor block just after the build
# publishes, so lib/build pre-fetches it with lib/fetch-signing-key into
# signing-key.asc. Long-lived workspaces are not subject to that race and can be
# fetched here.
emit_sources() {
	_workspace="$1"
	_key_file="${2-}"
	_uri="https://deb.${DEBUSINE_HOST}/${DEBUSINE_SCOPE}/${_workspace}/"
	if [ -n "$_key_file" ]; then
		_public_key=$(sed -e 's/^$/./;s/^/ /' "$_key_file")
	else
		_public_key=$(curl -fsSu "${DEBUSINE_USER}:${DEBUSINE_TOKEN}" "${_uri}signing-keys.asc"|sed -e 's/^$/./;s/^/ /')
	fi
	cat <<END
Types: deb deb-src
URIs: ${_uri}
Suites: ${SUITE}
Components: main contrib non-free non-free-firmware
Signed-By:
${_public_key}
END
}
