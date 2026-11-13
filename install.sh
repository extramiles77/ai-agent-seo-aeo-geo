#!/usr/bin/env bash
set -euo pipefail

# Ai Agent SEO Installer
# Wraps everything in main() to prevent partial execution on network failure

main() {
    SOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
    SKILL_DIR="${HOME}/.claude/skills/seo"
    AGENT_DIR="${HOME}/.claude/agents"

    echo "════════════════════════════════════════"
    echo "║   Ai Agent SEO - Installer             ║"
    echo "║   Installs from this checkout          ║"
    echo "════════════════════════════════════════"
    echo ""

    # Everything is copied from the checkout this script lives in. The runtime
    # launcher performs cross-platform Python resolution and validates the
    # minimum supported version, so no interpreter probing happens here.
    if [ ! -d "${SOURCE_DIR}/skills/seo" ]; then
        echo "✗ Cannot find skills/seo next to this script." >&2
        echo "  Run install.sh from the repository checkout." >&2
        exit 1
    fi

    # Create directories
    mkdir -p "${SKILL_DIR}"
    mkdir -p "${AGENT_DIR}"

    # Copy skill files
    echo "→ Installing skill files..."
    cp -r "${SOURCE_DIR}/skills/seo/"* "${SKILL_DIR}/"

    # Copy sub-skills
    if [ -d "${SOURCE_DIR}/skills" ]; then
        for skill_dir in "${SOURCE_DIR}/skills"/*/; do
            skill_name=$(basename "${skill_dir}")
            target="${HOME}/.claude/skills/${skill_name}"
            mkdir -p "${target}"
            cp -r "${skill_dir}"* "${target}/"
        done
    fi

    # Copy schema templates
    if [ -d "${SOURCE_DIR}/schema" ]; then
        mkdir -p "${SKILL_DIR}/schema"
        cp -r "${SOURCE_DIR}/schema/"* "${SKILL_DIR}/schema/"
    fi

    # Copy deterministic data files consumed by bundled scripts such as
    # seo_updates.py. Keep the repository-relative data/ layout intact.
    if [ -d "${SOURCE_DIR}/data" ]; then
        mkdir -p "${SKILL_DIR}/data"
        cp -r "${SOURCE_DIR}/data/"* "${SKILL_DIR}/data/"
    fi

    # Copy reference docs
    if [ -d "${SOURCE_DIR}/pdf" ]; then
        mkdir -p "${SKILL_DIR}/pdf"
        cp -r "${SOURCE_DIR}/pdf/"* "${SKILL_DIR}/pdf/"
    fi

    # Copy agents
    echo "→ Installing subagents..."
    cp -r "${SOURCE_DIR}/agents/"*.md "${AGENT_DIR}/" 2>/dev/null || true

    # Copy shared scripts
    if [ -d "${SOURCE_DIR}/scripts" ]; then
        mkdir -p "${SKILL_DIR}/scripts"
        cp -r "${SOURCE_DIR}/scripts/"* "${SKILL_DIR}/scripts/"
    fi

    # Copy the stable runtime launcher. It ships in scripts/ (never a top-level
    # bin/, which hosted marketplaces reject) and resolves runtime.py as a
    # sibling, so the manual layout below already matches the repository layout.
    if [ -f "${SOURCE_DIR}/scripts/claude-seo" ]; then
        mkdir -p "${SKILL_DIR}/scripts"
        cp "${SOURCE_DIR}/scripts/claude-seo" "${SKILL_DIR}/scripts/claude-seo"
        chmod +x "${SKILL_DIR}/scripts/claude-seo"
    fi

    # Copy hooks
    if [ -d "${SOURCE_DIR}/hooks" ]; then
        mkdir -p "${SKILL_DIR}/hooks"
        cp -r "${SOURCE_DIR}/hooks/"* "${SKILL_DIR}/hooks/"
        chmod +x "${SKILL_DIR}/hooks/"*.sh 2>/dev/null || true
        chmod +x "${SKILL_DIR}/hooks/"*.py 2>/dev/null || true
        # Manual installs copy hook files only; enforcement loads through the plugin manifest.
        echo "  Note: hook enforcement loads through the plugin manifest; manual hook copy is best-effort."
    fi

    # Copy extensions (optional add-ons: dataforseo, banana)
    if [ -d "${SOURCE_DIR}/extensions" ]; then
        echo "=> Installing extensions..."
        for ext_dir in "${SOURCE_DIR}/extensions"/*/; do
            [ -d "${ext_dir}" ] || continue
            ext_name=$(basename "${ext_dir}")
            # Extension skills
            if [ -d "${ext_dir}skills" ]; then
                for ext_skill in "${ext_dir}skills"/*/; do
                    [ -d "${ext_skill}" ] || continue
                    ext_skill_name=$(basename "${ext_skill}")
                    target="${HOME}/.claude/skills/${ext_skill_name}"
                    mkdir -p "${target}"
                    cp -r "${ext_skill}"* "${target}/"
                done
            fi
            # Extension agents
            if [ -d "${ext_dir}agents" ]; then
                cp -r "${ext_dir}agents/"*.md "${AGENT_DIR}/" 2>/dev/null || true
            fi
            # Extension references
            if [ -d "${ext_dir}references" ]; then
                mkdir -p "${SKILL_DIR}/extensions/${ext_name}/references"
                cp -r "${ext_dir}references/"* "${SKILL_DIR}/extensions/${ext_name}/references/"
            fi
            # Extension scripts
            if [ -d "${ext_dir}scripts" ]; then
                mkdir -p "${SKILL_DIR}/extensions/${ext_name}/scripts"
                cp -r "${ext_dir}scripts/"* "${SKILL_DIR}/extensions/${ext_name}/scripts/"
            fi
        done
    fi

    # Copy requirements.txt to skill dir so users can retry later
    cp "${SOURCE_DIR}/requirements.txt" "${SKILL_DIR}/requirements.txt" 2>/dev/null || true
    # pyproject.toml carries the version the runtime reports from a manual install.
    cp "${SOURCE_DIR}/pyproject.toml" "${SKILL_DIR}/pyproject.toml" 2>/dev/null || true

    # Manual installs have no ${CLAUDE_PLUGIN_ROOT}, so rewrite the canonical
    # launcher token to the absolute installed path. Rewrite only exact files
    # copied from this checkout during this install. The substitution is
    # idempotent: it consumes the plugin-root token, so a second pass matches
    # nothing. In a POSIX basic regular expression "$" is literal unless it ends
    # the expression, so ${CLAUDE_PLUGIN_ROOT} needs no escaping here.
    # Reference paths are opened with the Read tool, which does not expand
    # variables, so ${CLAUDE_PLUGIN_ROOT}/skills/ becomes the absolute path.
    skills_root_esc=$(printf '%s' "${HOME}/.claude/skills/" | sed 's/[#&\\]/\\&/g')
    rewrite_doc() {
        local doc="$1" temp_doc
        temp_doc="${doc}.claude-seo-tmp"
        sed -e "s#\${CLAUDE_PLUGIN_ROOT}/skills/#${skills_root_esc}#g" \
            -e 's#"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo" run#"$HOME/.claude/skills/seo/scripts/claude-seo" run#g' \
            -e 's#"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo" setup#"$HOME/.claude/skills/seo/scripts/claude-seo" setup#g' \
            -e 's#"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo" doctor#"$HOME/.claude/skills/seo/scripts/claude-seo" doctor#g' \
            "${doc}" > "${temp_doc}"
        mv "${temp_doc}" "${doc}"
    }
    for source_root in "${SOURCE_DIR}/skills"/*; do
        [ -d "${source_root}" ] || continue
        skill_name=$(basename "${source_root}")
        while IFS= read -r -d '' source_doc; do
            relative_doc=${source_doc#"${source_root}/"}
            doc="${HOME}/.claude/skills/${skill_name}/${relative_doc}"
            [ -f "${doc}" ] && rewrite_doc "${doc}"
        done < <(find "${source_root}" -type f -name '*.md' -print0)
    done
    for source_root in "${SOURCE_DIR}/extensions"/*/skills/*; do
        [ -d "${source_root}" ] || continue
        skill_name=$(basename "${source_root}")
        while IFS= read -r -d '' source_doc; do
            relative_doc=${source_doc#"${source_root}/"}
            doc="${HOME}/.claude/skills/${skill_name}/${relative_doc}"
            [ -f "${doc}" ] && rewrite_doc "${doc}"
        done < <(find "${source_root}" -type f -name '*.md' -print0)
    done
    for source_root in "${SOURCE_DIR}/extensions"/*/references; do
        [ -d "${source_root}" ] || continue
        ext_name=$(basename "$(dirname "${source_root}")")
        while IFS= read -r -d '' source_doc; do
            relative_doc=${source_doc#"${source_root}/"}
            doc="${SKILL_DIR}/extensions/${ext_name}/references/${relative_doc}"
            [ -f "${doc}" ] && rewrite_doc "${doc}"
        done < <(find "${source_root}" -type f -name '*.md' -print0)
    done
    for source_doc in "${SOURCE_DIR}/agents"/*.md "${SOURCE_DIR}/extensions"/*/agents/*.md; do
        [ -f "${source_doc}" ] || continue
        doc="${AGENT_DIR}/$(basename "${source_doc}")"
        [ -f "${doc}" ] && rewrite_doc "${doc}"
    done

    echo "→ Creating isolated Python runtime..."
    set +e
    "${SKILL_DIR}/scripts/claude-seo" setup
    runtime_status=$?
    set -e
    if [ "${runtime_status}" -ne 0 ] && [ "${runtime_status}" -ne 10 ]; then
        echo "✗ Core Python runtime setup failed. Installation is incomplete." >&2
        exit 1
    elif [ "${runtime_status}" -eq 10 ]; then
        echo "⚠ Core runtime installed, but Chromium setup is incomplete." >&2
    fi

    echo ""
    echo "✓ Ai Agent SEO installed successfully!"
    echo ""
    echo "Usage:"
    echo "  1. Start Claude Code:  claude"
    echo "  2. Run commands:       /seo audit https://example.com"
    echo ""
    echo "Python deps location: ${SKILL_DIR}/requirements.txt"
    echo "To uninstall: bash uninstall.sh  (from the checkout you installed from)"
}

main "$@"
