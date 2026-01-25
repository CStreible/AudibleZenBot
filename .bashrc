# VS Code shell integration — manual install
# Add this to enable VS Code terminal features (current working directory, command
# detection, decorations). Run `code ~/.bashrc` to open this file in VS Code.

# Only source the integration script when running inside VS Code and when
# the `code` CLI is available. For better startup performance you can run
# `code --locate-shell-integration-path bash` once and paste the resulting
# path here instead of calling `code` on every startup.

if command -v code >/dev/null 2>&1; then
  [[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path bash)"
fi
