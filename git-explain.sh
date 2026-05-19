#!/usr/bin/env bash
# ─────────────────────────────────────────────
#  git-explain  —  inspect & narrate git history
#  Usage:  ./git-explain.sh [path/to/repo]  [num_commits]
# ─────────────────────────────────────────────

set -euo pipefail

# ensure a TERM is set so tput / clear don't fail in minimal environments
export TERM="${TERM:-xterm}"

# ── colours ──────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
MAGENTA='\033[0;35m'
RED='\033[0;31m'
RESET='\033[0m'

# ── helpers ───────────────────────────────────
hr()  { printf "${DIM}%s${RESET}\n" "$(printf '─%.0s' {1..60})"; }
hdr() { printf "\n${BOLD}${CYAN}%s${RESET}\n" "$1"; hr; }

die() { printf "${RED}✖  %s${RESET}\n" "$1" >&2; exit 1; }

# ── args ──────────────────────────────────────
REPO_PATH="${1:-.}"
NUM_COMMITS="${2:-5}"

# ── validate ──────────────────────────────────
[[ -d "$REPO_PATH" ]] || die "Directory not found: $REPO_PATH"

cd "$REPO_PATH"

git rev-parse --is-inside-work-tree &>/dev/null \
  || die "Not a git repository: $(pwd)"

REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

# ── header ────────────────────────────────────
clear
printf "\n"
printf "${BOLD}${MAGENTA}  ██████╗ ██╗████████╗    ███████╗██╗  ██╗██████╗ ██╗      █████╗ ██╗███╗   ██╗\n"
printf "  ██╔════╝██║╚══██╔══╝    ██╔════╝╚██╗██╔╝██╔══██╗██║     ██╔══██╗██║████╗  ██║\n"
printf "  ██║     ██║   ██║       █████╗   ╚███╔╝ ██████╔╝██║     ███████║██║██╔██╗ ██║\n"
printf "  ██║     ██║   ██║       ██╔══╝   ██╔██╗ ██╔═══╝ ██║     ██╔══██║██║██║╚██╗██║\n"
printf "  ╚██████╗██║   ██║       ███████╗██╔╝ ██╗██║     ███████╗██║  ██║██║██║ ╚████║\n"
printf "   ╚═════╝╚═╝   ╚═╝       ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝${RESET}\n\n"

printf "  ${BOLD}Repo :${RESET} ${GREEN}%s${RESET}  ${DIM}(%s)${RESET}\n" "$REPO_NAME" "$REPO_ROOT"
printf "  ${BOLD}Showing last %s commits${RESET}\n\n" "$NUM_COMMITS"

# ── fetch commit hashes ───────────────────────
mapfile -t HASHES < <(git log --oneline -n "$NUM_COMMITS" --format="%H")

[[ ${#HASHES[@]} -gt 0 ]] || die "No commits found."

# ── per-commit analysis ───────────────────────
INDEX=1
for HASH in "${HASHES[@]}"; do

  # --- metadata ---
  SHORT=$(git rev-parse --short "$HASH")
  AUTHOR=$(git log -1 --format="%an" "$HASH")
  DATE=$(git log -1 --format="%cd" --date=format:"%Y-%m-%d %H:%M" "$HASH")
  MESSAGE=$(git log -1 --format="%s" "$HASH")
  BODY=$(git log -1 --format="%b" "$HASH")

  # --- changed files ---
  mapfile -t FILES < <(git diff-tree --no-commit-id -r --name-status "$HASH" 2>/dev/null || true)

  ADDED=0; MODIFIED=0; DELETED=0; RENAMED=0
  FILE_LIST=()

  for LINE in "${FILES[@]}"; do
    STATUS=$(echo "$LINE" | cut -f1)
    FNAME=$(echo  "$LINE" | cut -f2-)
    case "$STATUS" in
      A*)  ((ADDED++));    FILE_LIST+=("${GREEN}+${RESET} $FNAME") ;;
      M*)  ((MODIFIED++)); FILE_LIST+=("${YELLOW}~${RESET} $FNAME") ;;
      D*)  ((DELETED++));  FILE_LIST+=("${RED}-${RESET} $FNAME") ;;
      R*)  ((RENAMED++));  FILE_LIST+=("${CYAN}→${RESET} $FNAME") ;;
      *)   FILE_LIST+=("${DIM}?${RESET} $FNAME") ;;
    esac
  done

  TOTAL_FILES=$(( ADDED + MODIFIED + DELETED + RENAMED ))

  # ---- print commit header ----
  hdr "  Commit $INDEX / $NUM_COMMITS"

  printf "  ${BOLD}Hash   :${RESET} ${YELLOW}%s${RESET}\n"   "$SHORT  (${HASH})"
  printf "  ${BOLD}Author :${RESET} %s\n"                    "$AUTHOR"
  printf "  ${BOLD}Date   :${RESET} %s\n"                    "$DATE"
  printf "  ${BOLD}Message:${RESET} ${BOLD}%s${RESET}\n"     "$MESSAGE"
  [[ -n "$BODY" ]] && printf "  ${DIM}%s${RESET}\n" "$BODY"

  echo ""

  # ---- changed-file summary ----
  printf "  ${BOLD}Files changed: %d${RESET}  " "$TOTAL_FILES"
  (( ADDED    > 0 )) && printf "${GREEN}+%d added${RESET}  "    "$ADDED"
  (( MODIFIED > 0 )) && printf "${YELLOW}~%d modified${RESET}  " "$MODIFIED"
  (( DELETED  > 0 )) && printf "${RED}-%d deleted${RESET}  "   "$DELETED"
  (( RENAMED  > 0 )) && printf "${CYAN}→%d renamed${RESET}  "  "$RENAMED"
  echo ""
  echo ""

  for F in "${FILE_LIST[@]}"; do
    printf "    %b\n" "$F"
  done

  echo ""

  # ── AI-style explanation ─────────────────────
  printf "  ${BOLD}${MAGENTA}🔍 Explanation:${RESET}\n"

  # Determine intent from message keywords
  MSG_LOWER=$(echo "$Message $MESSAGE" | tr '[:upper:]' '[:lower:]')

  INTENT="general change"
  if   echo "$MSG_LOWER" | grep -qiE "fix|bug|patch|hotfix|repair|resolve|revert"; then
    INTENT="bug fix"
  elif echo "$MSG_LOWER" | grep -qiE "feat|feature|add|implement|introduce|new|creat"; then
    INTENT="new feature"
  elif echo "$MSG_LOWER" | grep -qiE "refactor|clean|reorgani|restructur|extract|move|rename|tidy"; then
    INTENT="refactor / cleanup"
  elif echo "$MSG_LOWER" | grep -qiE "test|spec|coverage|unit|e2e|assert"; then
    INTENT="test update"
  elif echo "$MSG_LOWER" | grep -qiE "doc|readme|changelog|comment|license|docs"; then
    INTENT="documentation"
  elif echo "$MSG_LOWER" | grep -qiE "style|format|lint|prettier|whitespace|indent"; then
    INTENT="style / formatting"
  elif echo "$MSG_LOWER" | grep -qiE "chore|build|ci|cd|deploy|release|version|bump|dep|package|npm|pip|yarn"; then
    INTENT="build / dependency / chore"
  elif echo "$MSG_LOWER" | grep -qiE "perf|optim|speed|cache|slow|fast|memory"; then
    INTENT="performance improvement"
  elif echo "$MSG_LOWER" | grep -qiE "securi|auth|token|password|vuln|cve|xss|sql|inject"; then
    INTENT="security"
  elif echo "$MSG_LOWER" | grep -qiE "merge|rebase"; then
    INTENT="merge / rebase"
  fi

  printf "  ${CYAN}Intent    :${RESET} ${BOLD}%s${RESET}\n" "$INTENT"

  # Build a plain-English description
  EXPLANATION=""

  if   (( TOTAL_FILES == 0 )); then
    EXPLANATION="This commit carries no file changes — it may be an empty commit, a tag, or a merge commit that brought no new diffs."
  elif (( ADDED > 0 && MODIFIED == 0 && DELETED == 0 )); then
    EXPLANATION="This commit adds $ADDED new file(s) without touching existing ones, suggesting new functionality or resources were introduced."
  elif (( DELETED > 0 && ADDED == 0 && MODIFIED == 0 )); then
    EXPLANATION="Only deletions — $DELETED file(s) removed. This may be cleanup, dead-code removal, or dropping a deprecated feature."
  elif (( RENAMED > 0 && MODIFIED == 0 && ADDED == 0 && DELETED == 0 )); then
    EXPLANATION="Pure renames/moves ($RENAMED file(s)). The codebase structure was reorganised with no content changes."
  elif (( MODIFIED > 0 && ADDED == 0 && DELETED == 0 )); then
    EXPLANATION="$MODIFIED existing file(s) were edited. Based on the commit message this looks like a $INTENT targeting files already in the project."
  else
    EXPLANATION="A mixed change: $ADDED added, $MODIFIED modified, $DELETED deleted, $RENAMED renamed. This suggests a broader $INTENT that touched multiple parts of the codebase."
  fi

  # Highlight notable file types
  EXT_LIST=""
  for F in "${FILE_LIST[@]}"; do
    EXT=$(echo "$F" | grep -oE '\.[a-zA-Z0-9]+$' | head -1 || true)
    [[ -n "$EXT" ]] && EXT_LIST+="$EXT "
  done

  UNIQUE_EXTS=$(echo "$EXT_LIST" | tr ' ' '\n' | sort -u | tr '\n' ' ')
  [[ -n "$UNIQUE_EXTS" ]] && \
    printf "  ${CYAN}File types:${RESET} %s\n" "$UNIQUE_EXTS"

  # Specific file-name hints
  NOTABLE=""
  for F in "${FILE_LIST[@]}"; do
    BASENAME=$(echo "$F" | awk '{print $NF}' | xargs basename 2>/dev/null || true)
    case "$BASENAME" in
      package.json|package-lock.json|yarn.lock|Pipfile*|requirements*.txt|pyproject.toml|go.mod|go.sum|Gemfile*)
        NOTABLE+="  • Dependency manifest changed → likely a library add/update/removal.\n" ;;
      *.test.*|*.spec.*|*_test.*|*_spec.*)
        NOTABLE+="  • Test file(s) included → the commit may add or update test coverage.\n" ;;
      README*|*.md|*.rst|CHANGELOG*)
        NOTABLE+="  • Documentation file(s) touched.\n" ;;
      Dockerfile*|docker-compose*|*.yml|*.yaml)
        NOTABLE+="  • Config / CI / container file(s) changed.\n" ;;
      *.sql|*migration*)
        NOTABLE+="  • Database migration or schema file detected.\n" ;;
    esac
  done

  # De-dup notable hints
  if [[ -n "$NOTABLE" ]]; then
    NOTABLE=$(printf "%b" "$NOTABLE" | sort -u)
  fi

  printf "  ${CYAN}Summary   :${RESET} %s\n" "$EXPLANATION"
  [[ -n "$NOTABLE" ]] && printf "${YELLOW}%b${RESET}" "$NOTABLE" | sed 's/^/  /'

  echo ""
  hr
  (( INDEX++ ))
done

# ── footer ────────────────────────────────────
printf "\n  ${BOLD}${GREEN}✔  Done.${RESET} Analysed ${BOLD}%d${RESET} commits in ${BOLD}%s${RESET}\n\n" \
  "${#HASHES[@]}" "$REPO_NAME"
