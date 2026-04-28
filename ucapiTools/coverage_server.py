#!/usr/bin/env python3
"""
Coverage Query Service - HTTP API Server
UCAPI 覆盖率查询服务，支持分段查询
"""

import json
import subprocess
import threading
import logging
import os
import re
import select
from pathlib import Path
from typing import Any
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==================== 配置 ====================

TOOL_PATH = Path("/home/c910/wangyahao/IntericSim/genUtil/CoverageExtractToolServer.exe")
DEFAULT_VDB = "/home/c910/wangyahao/openc910/smart_run/tb1/my_forcerv_test"
DEFAULT_TEST = "/home/c910/wangyahao/openc910/smart_run/tb1/my_forcerv_test.vdb/test1"

# 环境变量配置（必须与 makefile 一致）
ENV_CONFIG = {
    "CODE_BASE_PATH": "/home/c910/wangyahao/openc910/C910_RTL_FACTORY",
    "UCAPI_LIB": "/home/yian/Synopsys/vcs/V-2023.12-SP2/linux64/lib",
    "VCS_HOME": "/home/yian/Synopsys/vcs/V-2023.12-SP2"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UCAPI 输出段标记
SECTION_MARKERS = {
    "line": {
        "begin": "======================Line Coverage Begin========================",
        "end": "======================Line Coverage End========================",
    },
    "cond": {
        "begin": "======================Condition Coverage Begin========================",
        "end": "======================Condition Coverage End========================",
    },
    "tgl": {
        "begin": "======================Tgl Coverage Begin========================",
        "end": "======================Tgl Coverage End========================",
    },
    "fsm": {
        "begin": "======================Fsm Coverage Begin========================",
        "end": "======================Fsm Coverage End========================",
    },
    "branch": {
        "begin": "======================Branch Coverage Begin========================",
        "end": "======================Branch Coverage End========================",
    },
    "vp_summary": {
        "begin": "======================VP Summary Begin========================",
        "end": "======================VP Summary End========================",
    },
    "instance_score": {
        "begin": "======================Instance Coverage Score========================",
        "end": "======================Instance Coverage Score End========================",
    },
}

# VP kind 映射
VP_KIND_MAP = {
    "line": "line",
    "cond": "cond",
    "branch": "branch",
    "tgl": "tgl",
    "fsm": "fsm",
}


class CoverageService:
    """覆盖率查询服务客户端"""

    def __init__(self, tool_path: Path):
        self.tool_path = tool_path
        self.process = None
        self._lock = threading.Lock()
        self._init_service()

    def _init_service(self):
        """启动服务进程"""
        if not self.tool_path.exists():
            raise FileNotFoundError(f"C tool not found: {self.tool_path}")

        # 设置环境变量（关键！）
        env = os.environ.copy()
        env.update(ENV_CONFIG)
        ld_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{ENV_CONFIG['UCAPI_LIB']}:{ld_path}"

        self.process = subprocess.Popen(
            [str(self.tool_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        logger.info("Coverage service started")

        # 读取启动信息（带超时）
        ready = select.select([self.process.stdout], [], [], 5.0)
        if ready[0]:
            while True:
                try:
                    line = self.process.stdout.readline()
                    if "QUERY_END" in line or not line:
                        break
                except Exception:
                    break

    def _send_command(self, cmd: str) -> str:
        """发送命令并获取响应"""
        with self._lock:
            if self.process.poll() is not None:
                raise RuntimeError("C process has exited")

            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
            except BrokenPipeError:
                logger.error("Broken pipe when writing to C process")
                self._init_service()
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()

            response = []
            while True:
                try:
                    line = self.process.stdout.readline()
                    if not line:
                        logger.error("C process stdout closed unexpectedly")
                        break
                    if "QUERY_END" in line:
                        break
                    response.append(line)
                except Exception as e:
                    logger.error(f"Error reading from C process: {e}")
                    break
            return "".join(response)

    def _extract_section(self, raw_output: str, section_name: str) -> str | None:
        """提取指定段的内容"""
        markers = SECTION_MARKERS.get(section_name)
        if not markers:
            return None

        begin_idx = raw_output.find(markers["begin"])
        end_idx = raw_output.find(markers["end"])
        if begin_idx == -1 or end_idx == -1 or end_idx <= begin_idx:
            return None

        return raw_output[begin_idx + len(markers["begin"]):end_idx].strip()

    def _extract_query_coverage(self, output: str) -> str:
        """提取 Query Coverage Begin 和 End 之间的内容"""
        start_marker = "======================Query Coverage Begin========================"
        end_marker = "======================Query Coverage End========================"

        start_idx = output.find(start_marker)
        end_idx = output.find(end_marker)

        if start_idx == -1 or end_idx == -1:
            return output

        return output[start_idx + len(start_marker):end_idx].strip()

    def _normalize_module_name(self, module: str) -> str:
        """标准化模块名称，移除路径和后缀"""
        return Path(module).stem

    # ==================== 各段解析方法 ====================

    def _parse_line_coverage(self, raw_output: str) -> dict:
        """解析 Line Coverage 段"""
        section = self._extract_section(raw_output, "line")
        if not section:
            return {"status": "no_data", "lines": [], "covered": 0, "total": 0, "pct": 0.0}

        lines = []
        line_re = re.compile(r"Line\s+(\d+)\s+cover\s+status:\s*(Yes|No)\s*\|\s*(.*)")

        for line in section.splitlines():
            match = line_re.search(line)
            if match:
                lines.append({
                    "line_no": int(match.group(1)),
                    "covered": match.group(2) == "Yes",
                    "source": match.group(3).strip()
                })

        covered = sum(1 for l in lines if l["covered"])
        total = len(lines)
        pct = round(covered / total * 100, 2) if total > 0 else 0.0

        return {
            "status": "ok",
            "lines": lines,
            "covered": covered,
            "total": total,
            "pct": pct
        }

    def _parse_cond_coverage(self, raw_output: str) -> dict:
        """解析 Condition Coverage 段"""
        section = self._extract_section(raw_output, "cond")
        if not section:
            return {"status": "no_data", "conditions": [], "covered": 0, "total": 0, "pct": 0.0}

        conditions = []
        sub_cond_re = re.compile(
            r"Sub Condition\s*:\s*(.+?)\s*;\s*cover\s+status\s*:\s*(.+?)(?:\s+\(\d+/\d+\))?\s*$",
            re.MULTILINE
        )

        for match in sub_cond_re.finditer(section):
            cond_expr = match.group(1).strip()
            status_str = match.group(2).strip().lower()
            covered = "coverd" in status_str or "covered" in status_str
            conditions.append({
                "expression": cond_expr,
                "covered": covered
            })

        covered = sum(1 for c in conditions if c["covered"])
        total = len(conditions)
        pct = round(covered / total * 100, 2) if total > 0 else 0.0

        return {
            "status": "ok",
            "conditions": conditions,
            "covered": covered,
            "total": total,
            "pct": pct
        }

    def _parse_branch_coverage(self, raw_output: str) -> dict:
        """解析 Branch Coverage 段"""
        section = self._extract_section(raw_output, "branch")
        if not section:
            return {"status": "no_data", "branches": [], "covered": 0, "total": 0, "pct": 0.0}

        branches = []
        branch_re = re.compile(
            r"Branch:\s*(.+?)\s*;\s*line=(\d+)\s*;\s*(covered|not covered)\s*\((\d+)/(\d+)\)"
        )

        for match in branch_re.finditer(section):
            branches.append({
                "expression": match.group(1).strip(),
                "line_no": int(match.group(2)),
                "covered": match.group(3) == "covered",
                "covered_count": int(match.group(4)),
                "total_count": int(match.group(5))
            })

        covered = sum(b["covered_count"] for b in branches)
        total = sum(b["total_count"] for b in branches)
        pct = round(covered / total * 100, 2) if total > 0 else 0.0

        return {
            "status": "ok",
            "branches": branches,
            "covered": covered,
            "total": total,
            "pct": pct
        }

    def _parse_tgl_coverage(self, raw_output: str) -> dict:
        """解析 Toggle Coverage 段"""
        section = self._extract_section(raw_output, "tgl")
        if not section:
            return {"status": "no_data", "toggles": [], "covered": 0, "total": 0, "pct": 0.0}

        toggles = []
        tgl_re = re.compile(
            r"Toggle\s+(Signal|Vector):\s*(\S+)\s*;\s*line=(\d+)\s*;\s*(.+?)\s*;\s*ucapi=(\S+)"
        )

        for match in tgl_re.finditer(section):
            status_str = match.group(4).strip().lower()
            if "directional bins" in status_str:
                bins_match = re.search(r"directional bins=(\d+)/(\d+)", status_str)
                if bins_match:
                    covered = int(bins_match.group(1))
                    total = int(bins_match.group(2))
                else:
                    covered, total = 0, 0
            elif "no toggle" in status_str:
                covered, total = 0, 2
            elif "only one toggle" in status_str:
                covered, total = 1, 2
            else:
                covered, total = 0, 0

            toggles.append({
                "type": match.group(1).lower(),
                "signal": match.group(2),
                "line_no": int(match.group(3)),
                "covered": covered,
                "total": total,
                "status": status_str
            })

        covered = sum(t["covered"] for t in toggles)
        total = sum(t["total"] for t in toggles)
        pct = round(covered / total * 100, 2) if total > 0 else 0.0

        return {
            "status": "ok",
            "toggles": toggles,
            "covered": covered,
            "total": total,
            "pct": pct
        }

    def _parse_fsm_coverage(self, raw_output: str) -> dict:
        """解析 FSM Coverage 段"""
        section = self._extract_section(raw_output, "fsm")
        if not section:
            return {"status": "no_data", "fsms": [], "covered": 0, "total": 0, "pct": 0.0}

        fsms = []
        fsm_re = re.compile(
            r"FSM:\s*(\S+)\s*;\s*line=(\d+)\s*;\s*(covered|not covered)\s*\((\d+)/(\d+)\)\s*;\s*states=(\d+)\s*;\s*transitions=(\d+)"
        )

        for match in fsm_re.finditer(section):
            fsms.append({
                "name": match.group(1),
                "line_no": int(match.group(2)),
                "covered": match.group(3) == "covered",
                "covered_count": int(match.group(4)),
                "total_count": int(match.group(5)),
                "states": int(match.group(6)),
                "transitions": int(match.group(7))
            })

        covered = sum(f["covered_count"] for f in fsms)
        total = sum(f["total_count"] for f in fsms)
        pct = round(covered / total * 100, 2) if total > 0 else 0.0

        return {
            "status": "ok",
            "fsms": fsms,
            "covered": covered,
            "total": total,
            "pct": pct
        }

    def _parse_vp_summary(self, raw_output: str) -> dict | None:
        """解析 VP Summary 段"""
        section = self._extract_section(raw_output, "vp_summary")
        if not section:
            return None

        query = {}
        metrics = {}
        overall = {}

        for line in section.splitlines():
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split("\t")]
            if len(parts) < 3:
                continue

            record_type = parts[0]
            fields = {}
            for i in range(1, len(parts) - 1, 2):
                fields[parts[i]] = parts[i + 1] if i + 1 < len(parts) else ""

            if record_type == "VP_QUERY":
                query = {
                    "module": fields.get("module", ""),
                    "range": fields.get("range", ""),
                    "qualified_instance": fields.get("qualified_instance", ""),
                    "source_file": fields.get("source_file", ""),
                }
            elif record_type == "VP_METRIC":
                kind = fields.get("kind", "")
                if kind:
                    metrics[kind] = {
                        "kind": kind,
                        "covered": int(fields.get("covered", "0") or 0),
                        "coverable": int(fields.get("coverable", "0") or 0),
                        "pct": round(float(fields.get("pct", "0") or 0), 2),
                        "matched": int(fields.get("matched", "0") or 0),
                    }
            elif record_type == "VP_OVERALL":
                overall = {
                    "pct": round(float(fields.get("pct", "0") or 0), 2),
                    "metric_count": int(fields.get("metric_count", "0") or 0),
                }

        return {"query": query, "metrics": metrics, "overall": overall}

    def _parse_instance_score(self, raw_output: str) -> dict | None:
        """解析 Instance Coverage Score 段"""
        section = self._extract_section(raw_output, "instance_score")
        if not section:
            return None

        result = {
            "instance_name": "",
            "rtl_file": "",
            "scores": {}
        }

        for line in section.splitlines():
            line = line.strip()
            if line.startswith("instance name is"):
                result["instance_name"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("rtl file name is"):
                result["rtl_file"] = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("Score :"):
                score_match = re.search(r"Score\s*:\s*([\d.]+)", line)
                if score_match:
                    result["scores"]["overall"] = float(score_match.group(1))

                for metric in ["Line", "Condition", "Tgl", "Fsm", "Branch"]:
                    metric_match = re.search(rf"{metric}\s*:\s*([\d.]+)", line)
                    if metric_match:
                        result["scores"][metric.lower()] = float(metric_match.group(1))

        return result

    # ==================== 查询方法 ====================

    def query(self, vdb_path: str, test_name: str, module: str,
              start_line: int, end_line: int) -> dict:
        """基础查询，返回原始输出"""
        if self.process.poll() is not None:
            logger.warning("C process exited, restarting...")
            self._init_service()

        module_name = self._normalize_module_name(module)

        if test_name.startswith('/'):
            test_path = test_name
        else:
            test_path = f"{vdb_path}/{test_name}" if vdb_path.endswith('.vdb') else f"{vdb_path}.vdb/{test_name}"

        cmd = f"{vdb_path} {test_path} {module_name} {start_line}-{end_line}"
        logger.debug(f"Command: {cmd}")

        try:
            output = self._send_command(cmd)
        except BrokenPipeError as e:
            logger.error(f"Broken pipe, restarting: {e}")
            self._init_service()
            output = self._send_command(cmd)

        coverage_output = self._extract_query_coverage(output)

        return {
            "module": module_name,
            "range": f"{start_line}-{end_line}",
            "raw_output": coverage_output,
        }

    def close(self):
        """关闭服务"""
        if self.process:
            try:
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            logger.info("Coverage service stopped")


# 全局服务实例
service = None


# ==================== API 端点 ====================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    if service and service.process and service.process.poll() is None:
        return jsonify({"status": "healthy", "service": "coverage_query"})
    return jsonify({"status": "unhealthy", "service": "coverage_query"}), 503


@app.route('/api/v1/query', methods=['POST'])
def query_coverage():
    """
    查询覆盖率 - 根据 kind 参数返回对应的覆盖率信息
    
    kind 参数支持多选，用 + 连接：
    - "line": Line Coverage
    - "cond" 或 "condition": Condition Coverage  
    - "branch": Branch Coverage
    - "tgl": Toggle Coverage
    - "fsm": FSM Coverage
    - "vp": VP Summary (各 kind 汇总)
    - "score" 或 "instance_score": Instance Coverage Score
    - "raw": 返回原始输出
    
    示例：
    - "kind": "line" → 只返回 line 覆盖率
    - "kind": "line+cond" → 返回 line 和 condition 覆盖率
    - "kind": "line+vp+raw" → 返回 line、vp 和原始输出
    - 不传 kind → 返回原始 raw_output
    """
    try:
        data = request.json
        kind_param = data.get("kind", "")

        # 基础查询
        result = service.query(
            vdb_path=data.get("vdb_path", DEFAULT_VDB),
            test_name=data.get("test_name", DEFAULT_TEST),
            module=data["module"],
            start_line=data["start_line"],
            end_line=data["end_line"]
        )

        # 【关键】如果没有 kind 参数，直接返回原始输出
        if not kind_param:
            return jsonify({"success": True, "data": result})

        # 解析 kind 参数（支持 + 分隔的多选）
        kinds = [k.strip().lower() for k in kind_param.replace("+", ",").split(",")]
        kinds = list(set(kinds))  # 去重

        raw_output = result["raw_output"]
        # 记录请求的主要 kind（取第一个非 vp/raw 的 kind），供 scheduler 解析使用
        # scheduler 发送的是单个 kind + vp，如 "branch+vp"
        primary_kind = None
        for k in kinds:
            if k not in ["vp", "raw"]:
                primary_kind = k
                break
        primary_kind = primary_kind or "line"
        response_data = {
            "module": result["module"],
            "range": result["range"],
            "kind": primary_kind,  # 添加 kind 字段，scheduler 需要用它确定 VP 类型
        }

        # 检查是否需要返回原始输出
        include_raw = "raw" in kinds
        if include_raw:
            kinds = [k for k in kinds if k != "raw"]
            response_data["raw_output"] = raw_output

        # 解析 VP Summary（多个 kind 可能需要）
        vp_summary = None
        if any(k in kinds for k in ["line", "cond", "condition", "branch", "tgl", "fsm", "vp"]):
            vp_summary = service._parse_vp_summary(raw_output)

        # 根据选择的 kind 返回对应字段
        for k in kinds:
            if k == "line":
                parsed = service._parse_line_coverage(raw_output)
                response_data["line"] = {
                    "status": parsed["status"],
                    "covered": parsed["covered"],
                    "total": parsed["total"],
                    "pct": parsed["pct"],
                    "lines": parsed["lines"] if parsed["lines"] else None,
                }
            elif k in ["cond", "condition"]:
                parsed = service._parse_cond_coverage(raw_output)
                response_data["condition"] = {
                    "status": parsed["status"],
                    "covered": parsed["covered"],
                    "total": parsed["total"],
                    "pct": parsed["pct"],
                    "conditions": parsed["conditions"] if parsed["conditions"] else None,
                }
            elif k == "branch":
                parsed = service._parse_branch_coverage(raw_output)
                response_data["branch"] = {
                    "status": parsed["status"],
                    "covered": parsed["covered"],
                    "total": parsed["total"],
                    "pct": parsed["pct"],
                    "branches": parsed["branches"] if parsed["branches"] else None,
                }
            elif k == "tgl":
                parsed = service._parse_tgl_coverage(raw_output)
                response_data["toggle"] = {
                    "status": parsed["status"],
                    "covered": parsed["covered"],
                    "total": parsed["total"],
                    "pct": parsed["pct"],
                    "toggles": parsed["toggles"] if parsed["toggles"] else None,
                }
            elif k == "fsm":
                parsed = service._parse_fsm_coverage(raw_output)
                response_data["fsm"] = {
                    "status": parsed["status"],
                    "covered": parsed["covered"],
                    "total": parsed["total"],
                    "pct": parsed["pct"],
                    "fsms": parsed["fsms"] if parsed["fsms"] else None,
                }
            elif k == "vp":
                if vp_summary:
                    query_info = vp_summary.get("query", {})
                    response_data["vp"] = {
                        "query": query_info,
                        "metrics": vp_summary.get("metrics", {}),
                        "overall": vp_summary.get("overall", {}),
                    }
                else:
                    response_data["vp"] = None
            elif k in ["score", "instance_score"]:
                parsed = service._parse_instance_score(raw_output)
                response_data["instance_score"] = parsed

        # # 如果只选了一个 kind 且没有 raw，也返回原始输出（方便调试）
        # if len(kinds) == 1 and not include_raw:
        #     response_data["raw_output"] = raw_output

        return jsonify({"success": True, "data": response_data})
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def init_service():
    """初始化服务"""
    global service
    service = CoverageService(TOOL_PATH)


if __name__ == '__main__':
    init_service()
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        service.close()