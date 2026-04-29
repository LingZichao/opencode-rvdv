#!/usr/bin/env bash
set -u
set -o pipefail

# Linear OpenCode generator benchmark for manual_trace_seed.
#
# This follows the documented OpenCode automation surface:
#   opencode run --agent <agent> --model <provider/model> --file <path>
# It runs every manual case as an isolated non-interactive session and records
# enough metadata for later manual scoring.

usage() {
  cat <<'EOF'
Usage:
  scripts/run-manual-generator-benchmark.sh [options] [case_name_or_path ...]

Options:
  --model MODEL          OpenCode model id, provider/model format.
                         Default: localmodel/qwen3.5-9b@q8_0
  --agent AGENT          OpenCode agent name. Default: generator
  --run-id ID            Run id under workspace/manual_generator_runs/.
                         Default: UTC timestamp
  --cases-root DIR       Manual cases root. Default: manual_trace_seed/cases
  --bench-root DIR       Benchmark log root. Default: workspace/manual_generator_runs
  --attach URL           Attach to a running `opencode serve` backend.
  --format FORMAT        opencode output format: json or default. Default: json
  --start-at CASE        Skip sorted cases until this case basename appears.
  --max N                Run at most N cases after filtering.
  --resume               Skip cases already marked success in this run id.
  --stop-on-failure      Stop the batch at the first failed case.
  --dry-run              Print selected cases and command shape without running.
  -h, --help             Show this help.

Environment overrides:
  OPENCODE_GENERATOR_MODEL     Same as --model.
  OPENCODE_GENERATOR_AGENT     Same as --agent.
  OPENCODE_ATTACH              Same as --attach.
  OPENCODE_CONFIG              Config path. Defaults to ./opencode.jsonc if present.
  MANUAL_RUN_ID                Same as --run-id.
  MANUAL_CASE_TIMEOUT          Optional timeout value accepted by `timeout`, e.g. 45m.
  MANUAL_SKIP_PERMISSIONS      Default 1. Passes --dangerously-skip-permissions.
  MANUAL_LIVE_LOG              Default 0. Set 1 to tee each OpenCode log live.

Examples:
  scripts/run-manual-generator-benchmark.sh
  scripts/run-manual-generator-benchmark.sh --max 3
  scripts/run-manual-generator-benchmark.sh --attach http://localhost:4096
  OPENCODE_GENERATOR_MODEL=localmodel/qwopus3.5-9b@q8_0 scripts/run-manual-generator-benchmark.sh case_004_floating_data_constraint
EOF
}

die() {
  echo "error: $*" >&2
  exit 1
}

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

csv_cell() {
  local s="$1"
  s="${s//\"/\"\"}"
  printf '"%s"' "$s"
}

utc_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

MODEL="${OPENCODE_GENERATOR_MODEL:-localmodel/qwen3.5-9b@q8_0}"
AGENT="${OPENCODE_GENERATOR_AGENT:-generator}"
RUN_ID="${MANUAL_RUN_ID:-$(date -u +%Y%m%d-%H%M%S)}"
CASES_ROOT="$PROJECT_ROOT/manual_trace_seed/cases"
BENCH_ROOT="$PROJECT_ROOT/workspace/manual_generator_runs"
ATTACH="${OPENCODE_ATTACH:-}"
FORMAT="${OPENCODE_RUN_FORMAT:-json}"
START_AT=""
MAX_CASES=""
RESUME=0
STOP_ON_FAILURE=0
DRY_RUN=0
POSITIONAL_CASES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      [[ $# -ge 2 ]] || die "--model requires a value"
      MODEL="$2"
      shift 2
      ;;
    --agent)
      [[ $# -ge 2 ]] || die "--agent requires a value"
      AGENT="$2"
      shift 2
      ;;
    --run-id)
      [[ $# -ge 2 ]] || die "--run-id requires a value"
      RUN_ID="$2"
      shift 2
      ;;
    --cases-root)
      [[ $# -ge 2 ]] || die "--cases-root requires a value"
      CASES_ROOT="$2"
      shift 2
      ;;
    --bench-root)
      [[ $# -ge 2 ]] || die "--bench-root requires a value"
      BENCH_ROOT="$2"
      shift 2
      ;;
    --attach)
      [[ $# -ge 2 ]] || die "--attach requires a value"
      ATTACH="$2"
      shift 2
      ;;
    --format)
      [[ $# -ge 2 ]] || die "--format requires a value"
      FORMAT="$2"
      shift 2
      ;;
    --start-at)
      [[ $# -ge 2 ]] || die "--start-at requires a value"
      START_AT="$2"
      shift 2
      ;;
    --max)
      [[ $# -ge 2 ]] || die "--max requires a value"
      MAX_CASES="$2"
      shift 2
      ;;
    --resume)
      RESUME=1
      shift
      ;;
    --stop-on-failure)
      STOP_ON_FAILURE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        POSITIONAL_CASES+=("$1")
        shift
      done
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      POSITIONAL_CASES+=("$1")
      shift
      ;;
  esac
done

[[ "$FORMAT" == "json" || "$FORMAT" == "default" ]] || die "--format must be json or default"
[[ "$MODEL" == */* ]] || die "model must use provider/model format, got: $MODEL"
[[ "$CASES_ROOT" == /* ]] || CASES_ROOT="$PROJECT_ROOT/$CASES_ROOT"
[[ "$BENCH_ROOT" == /* ]] || BENCH_ROOT="$PROJECT_ROOT/$BENCH_ROOT"
[[ -d "$CASES_ROOT" ]] || die "cases root not found: $CASES_ROOT"
command -v opencode >/dev/null 2>&1 || die "opencode command not found"

if [[ -z "${OPENCODE_CONFIG:-}" && -f "$PROJECT_ROOT/opencode.jsonc" ]]; then
  export OPENCODE_CONFIG="$PROJECT_ROOT/opencode.jsonc"
fi
export OPENCODE_DISABLE_AUTOUPDATE="${OPENCODE_DISABLE_AUTOUPDATE:-true}"

if [[ -n "${OPENCODE_CONFIG:-}" && ! -f "$OPENCODE_CONFIG" ]]; then
  die "OPENCODE_CONFIG does not exist: $OPENCODE_CONFIG"
fi

resolve_case() {
  local item="$1"
  if [[ -d "$item" ]]; then
    cd "$item" && pwd
    return
  fi
  if [[ -d "$CASES_ROOT/$item" ]]; then
    cd "$CASES_ROOT/$item" && pwd
    return
  fi
  if [[ "$item" =~ ^[0-9]+$ ]]; then
    local padded
    padded="$(printf 'case_%03d' "$item")"
    local match
    match="$(find "$CASES_ROOT" -mindepth 1 -maxdepth 1 -type d -name "${padded}_*" | sort | head -n 1)"
    [[ -n "$match" ]] && { cd "$match" && pwd; return; }
  fi
  local loose
  loose="$(find "$CASES_ROOT" -mindepth 1 -maxdepth 1 -type d -name "*$item*" | sort | head -n 1)"
  [[ -n "$loose" ]] && { cd "$loose" && pwd; return; }
  return 1
}

discover_cases() {
  if [[ ${#POSITIONAL_CASES[@]} -gt 0 ]]; then
    local item
    for item in "${POSITIONAL_CASES[@]}"; do
      resolve_case "$item" || die "case not found: $item"
    done
  else
    find "$CASES_ROOT" -mindepth 1 -maxdepth 1 -type d -name "case_*" | sort
  fi
}

mapfile -t SELECTED_CASES < <(discover_cases)

if [[ -n "$START_AT" ]]; then
  filtered=()
  seen=0
  for case_dir in "${SELECTED_CASES[@]}"; do
    case_name="$(basename "$case_dir")"
    if [[ "$seen" -eq 0 && "$case_name" == "$START_AT" ]]; then
      seen=1
    fi
    if [[ "$seen" -eq 1 ]]; then
      filtered+=("$case_dir")
    fi
  done
  [[ "$seen" -eq 1 ]] || die "--start-at case not found in selected cases: $START_AT"
  SELECTED_CASES=("${filtered[@]}")
fi

if [[ -n "$MAX_CASES" ]]; then
  [[ "$MAX_CASES" =~ ^[0-9]+$ ]] || die "--max must be a number"
  SELECTED_CASES=("${SELECTED_CASES[@]:0:$MAX_CASES}")
fi

[[ ${#SELECTED_CASES[@]} -gt 0 ]] || die "no cases selected"

RUN_DIR="$BENCH_ROOT/$RUN_ID"
SUMMARY_CSV="$RUN_DIR/summary.csv"

if [[ "$DRY_RUN" -eq 0 ]]; then
  mkdir -p "$RUN_DIR"
  ln -sfn "$RUN_DIR" "$BENCH_ROOT/latest"
  {
    echo "RUN_ID=$RUN_ID"
    echo "MODEL=$MODEL"
    echo "AGENT=$AGENT"
    echo "FORMAT=$FORMAT"
    echo "ATTACH=$ATTACH"
    echo "OPENCODE_CONFIG=${OPENCODE_CONFIG:-}"
    echo "PROJECT_ROOT=$PROJECT_ROOT"
    echo "CASES_ROOT=$CASES_ROOT"
    echo "STARTED_AT=$(utc_now)"
  } > "$RUN_DIR/run_config.env"
  printf 'case,task_name,status,exit_code,duration_sec,test_plan,script_dir,log,status_json\n' > "$SUMMARY_CSV"
fi

echo "Manual generator benchmark"
echo "  model:  $MODEL"
echo "  agent:  $AGENT"
echo "  cases:  ${#SELECTED_CASES[@]}"
echo "  run:    $RUN_DIR"
if [[ -n "$ATTACH" ]]; then
  echo "  attach: $ATTACH"
fi

FAILURES=0

for case_dir in "${SELECTED_CASES[@]}"; do
  case_name="$(basename "$case_dir")"
  plan_file="$case_dir/test_plan.md"
  manifest_file="$case_dir/manifest.yaml"
  [[ -f "$plan_file" ]] || die "missing test_plan.md for $case_name"

  task_name="$case_name"
  if [[ -f "$manifest_file" ]]; then
    manifest_task="$(awk -F': *' '/^task_name:/ { print $2; exit }' "$manifest_file")"
    [[ -n "$manifest_task" ]] && task_name="$manifest_task"
  fi

  case_out="$RUN_DIR/$case_name"
  script_out="$PROJECT_ROOT/workspace/isgScripts/manual_benchmark/$RUN_ID/$case_name"
  log_file="$case_out/opencode.${FORMAT}.log"
  prompt_file="$case_out/prompt.md"
  status_file="$case_out/status.json"
  marker_file="$case_out/.started"

  if [[ "$RESUME" -eq 1 && -f "$status_file" ]] && grep -q '"status": "success"' "$status_file"; then
    echo "==> $case_name: already successful, skipping"
    continue
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "==> $case_name"
    echo "    plan:       $plan_file"
    echo "    script_dir: $script_out"
    echo "    command:    opencode run --agent $AGENT --model $MODEL --file <copied test_plan.md>"
    continue
  fi

  mkdir -p "$case_out" "$script_out"
  cp "$plan_file" "$case_out/test_plan.md"
  if [[ -f "$manifest_file" ]]; then
    cp "$manifest_file" "$case_out/manifest.yaml"
  fi

  cat > "$prompt_file" <<EOF
你正在执行 OpenCode-RVDV manual generator benchmark 的一个独立 case。

Case: $case_name
Task name: $task_name
指定输出目录: $script_out

请只把附加的 test_plan.md 当作 generator 输入需求。manifest.yaml、unit_catalog.yaml 以及 manual_trace_seed 的标注元数据只用于评测，不允许读取或引用。

请按 .opencode/prompts/generator.md 的职责执行：
1. 阅读附加 test_plan.md，生成一个完整 FORCE-RISCV Python ISG 脚本到指定输出目录。
2. 需要时查阅 workspace/agentDoc/forceRV/ 下的本地文档与示例。
3. 使用 isg-compile skill 编译；编译失败时只修复当前脚本并重试。
4. 编译成功后使用 gem5-prescreen skill 做预筛选；引用 output.log 或 m5out/stats.txt 的具体证据。
5. 不执行 RTL/VCS 仿真，不创建覆盖率 VDB。
6. 不要提问；如果由于环境或需求不可执行，请在输出目录写一个 failure_report.md，并在最终回复说明阻塞点。
7. 必须实际创建脚本文件或 failure_report.md；不能只回复计划、思路或下一步。
8. 编译/预筛选必须调用对应 skill 的 CLI；不要绕过 skill 直接调用 friscv/gem5，也不要用管道、head、tail 截断验证命令，避免吞掉失败退出码。

最终回复必须包含：
- 脚本路径
- 编译结果
- gem5 run_id 或 failure_report.md 路径
- 关键证据
- 仍然不足的点
EOF

  echo "==> $case_name: start $(utc_now)"
  echo "    log:        $log_file"
  echo "    script_dir: $script_out"

  touch "$marker_file"
  start_epoch="$(date +%s)"
  start_iso="$(utc_now)"

  cmd=(
    opencode run
    --dir "$PROJECT_ROOT"
    --agent "$AGENT"
    --model "$MODEL"
    --format "$FORMAT"
    --title "manual-generator/$RUN_ID/$case_name"
    --file "$case_out/test_plan.md"
  )

  if [[ -n "$ATTACH" ]]; then
    cmd+=(--attach "$ATTACH")
  fi

  if [[ "${MANUAL_SKIP_PERMISSIONS:-1}" == "1" ]]; then
    cmd+=(--dangerously-skip-permissions)
  fi

  message="$(< "$prompt_file")"
  run_cmd=("${cmd[@]}" "$message")
  if [[ -n "${MANUAL_CASE_TIMEOUT:-}" ]]; then
    run_cmd=(timeout "$MANUAL_CASE_TIMEOUT" "${run_cmd[@]}")
  fi

  exit_code=0
  if [[ "${MANUAL_LIVE_LOG:-0}" == "1" ]]; then
    "${run_cmd[@]}" 2>&1 | tee "$log_file"
    exit_code="${PIPESTATUS[0]}"
  else
    "${run_cmd[@]}" > "$log_file" 2>&1
    exit_code="$?"
  fi

  end_epoch="$(date +%s)"
  end_iso="$(utc_now)"
  duration="$((end_epoch - start_epoch))"

  find "$script_out" -maxdepth 6 -type f | sort > "$case_out/generated_files.txt" 2>/dev/null || true
  find "$PROJECT_ROOT/workspace/isgScripts" -type f -newer "$marker_file" | sort > "$case_out/workspace_new_files.txt" 2>/dev/null || true

  artifact_count="$(wc -l < "$case_out/generated_files.txt" | tr -d ' ')"
  failure_report_count="$(find "$script_out" -maxdepth 6 -type f -name 'failure_report.md' | wc -l | tr -d ' ')"
  compile_artifact_count="$(find "$script_out" -maxdepth 8 -type f \( -name '*.ELF' -o -name '*.Default.ELF' \) | wc -l | tr -d ' ')"
  gem5_evidence_count="$(find "$script_out" -maxdepth 10 -type f \( -name 'output.log' -o -name 'manifest.json' -o -path '*/m5out/stats.txt' \) | wc -l | tr -d ' ')"
  status="success"
  if [[ "$exit_code" -ne 0 ]]; then
    status="failed"
    if [[ "$exit_code" -eq 124 ]]; then
      status="timeout"
    fi
    FAILURES="$((FAILURES + 1))"
  elif [[ "$failure_report_count" -gt 0 ]]; then
    status="reported_failure"
    FAILURES="$((FAILURES + 1))"
  elif [[ "$artifact_count" -eq 0 ]]; then
    status="no_artifact"
    FAILURES="$((FAILURES + 1))"
  elif [[ "$compile_artifact_count" -eq 0 || "$gem5_evidence_count" -eq 0 ]]; then
    status="incomplete_validation"
    FAILURES="$((FAILURES + 1))"
  fi

  session_id="$(sed -n 's/.*"sessionID":"\([^"]*\)".*/\1/p; s/.*"sessionId":"\([^"]*\)".*/\1/p' "$log_file" | head -n 1 || true)"

  {
    printf '{\n'
    printf '  "case": "%s",\n' "$(json_escape "$case_name")"
    printf '  "task_name": "%s",\n' "$(json_escape "$task_name")"
    printf '  "status": "%s",\n' "$(json_escape "$status")"
    printf '  "exit_code": %s,\n' "$exit_code"
    printf '  "duration_sec": %s,\n' "$duration"
    printf '  "artifact_count": %s,\n' "$artifact_count"
    printf '  "failure_report_count": %s,\n' "$failure_report_count"
    printf '  "compile_artifact_count": %s,\n' "$compile_artifact_count"
    printf '  "gem5_evidence_count": %s,\n' "$gem5_evidence_count"
    printf '  "started_at": "%s",\n' "$start_iso"
    printf '  "ended_at": "%s",\n' "$end_iso"
    printf '  "model": "%s",\n' "$(json_escape "$MODEL")"
    printf '  "agent": "%s",\n' "$(json_escape "$AGENT")"
    printf '  "session_id": "%s",\n' "$(json_escape "$session_id")"
    printf '  "test_plan": "%s",\n' "$(json_escape "$case_out/test_plan.md")"
    printf '  "script_dir": "%s",\n' "$(json_escape "$script_out")"
    printf '  "log": "%s"\n' "$(json_escape "$log_file")"
    printf '}\n'
  } > "$status_file"

  {
    csv_cell "$case_name"; printf ','
    csv_cell "$task_name"; printf ','
    csv_cell "$status"; printf ','
    csv_cell "$exit_code"; printf ','
    csv_cell "$duration"; printf ','
    csv_cell "$case_out/test_plan.md"; printf ','
    csv_cell "$script_out"; printf ','
    csv_cell "$log_file"; printf ','
    csv_cell "$status_file"; printf '\n'
  } >> "$SUMMARY_CSV"

  echo "==> $case_name: $status in ${duration}s"
  if [[ "$status" != "success" && "$STOP_ON_FAILURE" -eq 1 ]]; then
    echo "Stopping at first failure as requested."
    break
  fi
done

if [[ "$DRY_RUN" -eq 1 ]]; then
  exit 0
fi

{
  echo "FINISHED_AT=$(utc_now)"
  echo "FAILURES=$FAILURES"
} >> "$RUN_DIR/run_config.env"

echo "Benchmark finished"
echo "  summary: $SUMMARY_CSV"
echo "  failures: $FAILURES"

if [[ "$FAILURES" -gt 0 ]]; then
  exit 1
fi
