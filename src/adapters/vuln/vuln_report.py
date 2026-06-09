"""Vulnerability Report Generator

Generates vulnerability reports in multiple formats (JSON, HTML, Markdown)
from unified scan results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .vuln_parser import (
    VulnScanResult,
    VulnerabilityFinding,
    VulnSeverity,
    VulnCategory,
    UnifiedVulnParser,
)

logger = logging.getLogger(__name__)


class VulnReportGenerator:
    """Generates vulnerability reports from unified scan results."""

    def __init__(self, output_dir: str = "./reports/vuln"):
        """Initialize report generator.

        Args:
            output_dir: Directory to store generated reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json(self, result: VulnScanResult, filename: Optional[str] = None) -> str:
        """Generate JSON vulnerability report.

        Args:
            result: VulnScanResult to format
            filename: Optional custom filename

        Returns:
            Path to the generated report file
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"vuln_scan_{result.scanner}_{result.target[:32]}_{timestamp}.json"

        report_path = self.output_dir / filename

        # Build OWASP-compatible report
        report = UnifiedVulnParser.to_owasp_format(result)

        report_data = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "report_version": "1.0.0",
                "scanner": result.scanner,
                "report_type": "vulnerability_scan",
            },
            "scan_summary": {
                "scan_id": result.scan_id,
                "target": result.target,
                "scan_type": result.scan_type,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "duration_seconds": result.duration_seconds,
            },
            "summary": {
                "total": result.total_findings,
                "critical": result.critical_count,
                "high": result.high_count,
                "medium": result.medium_count,
                "low": result.low_count,
                "info": result.info_count,
            },
            "risk_assessment": report,
            "findings": [f.to_dict() for f in result.findings],
            "raw_output": result.raw_output,
        }

        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"JSON report generated: {report_path}")
        return str(report_path)

    def generate_html(self, result: VulnScanResult, filename: Optional[str] = None) -> str:
        """Generate HTML vulnerability report with interactive features.

        Args:
            result: VulnScanResult to format
            filename: Optional custom filename

        Returns:
            Path to the generated report file
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"vuln_report_{result.scanner}_{timestamp}.html"

        report_path = self.output_dir / filename

        # Generate severity bar items
        severity_bars = self._render_severity_bars(result)
        findings_rows = self._render_findings_table(result.findings)
        risk_level, risk_score = self._calculate_risk(result)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vulnerability Scan Report - {result.target}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #0f172a; color: #e2e8f0; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1e293b, #334155);
                   border-radius: 12px; padding: 30px; margin-bottom: 24px;
                   border: 1px solid #475569; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; color: #f1f5f9; }}
        .header .meta {{ color: #94a3b8; font-size: 14px; }}
        .header .meta span {{ margin-right: 20px; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                         gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #1e293b; border-radius: 10px; padding: 20px; text-align: center;
                 border: 1px solid #334155; }}
        .card .count {{ font-size: 36px; font-weight: 700; }}
        .card .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
                       color: #94a3b8; margin-top: 4px; }}
        .card.critical {{ border-color: #ef4444; }}
        .card.critical .count {{ color: #ef4444; }}
        .card.high {{ border-color: #f97316; }}
        .card.high .count {{ color: #f97316; }}
        .card.medium {{ border-color: #eab308; }}
        .card.medium .count {{ color: #eab308; }}
        .card.low {{ border-color: #22c55e; }}
        .card.low .count {{ color: #22c55e; }}
        .card.info {{ border-color: #3b82f6; }}
        .card.info .count {{ color: #3b82f6; }}
        .card.total {{ border-color: #8b5cf6; }}
        .card.total .count {{ color: #8b5cf6; }}
        .risk-badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px;
                       font-weight: 600; font-size: 14px; }}
        .risk-critical {{ background: #ef4444; color: #fff; }}
        .risk-high {{ background: #f97316; color: #fff; }}
        .risk-medium {{ background: #eab308; color: #1e293b; }}
        .risk-low {{ background: #22c55e; color: #1e293b; }}
        .severity-section {{ background: #1e293b; border-radius: 10px; padding: 20px;
                            border: 1px solid #334155; margin-bottom: 24px; }}
        .severity-section h2 {{ font-size: 18px; margin-bottom: 16px; color: #f1f5f9; }}
        .bar-container {{ margin-bottom: 12px; }}
        .bar-label {{ display: flex; justify-content: space-between; margin-bottom: 4px;
                      font-size: 13px; }}
        .bar {{ height: 24px; background: #0f172a; border-radius: 6px; overflow: hidden; }}
        .bar-fill {{ height: 100%; border-radius: 6px; transition: width 0.5s ease; }}
        .bar-fill.critical {{ background: #ef4444; }}
        .bar-fill.high {{ background: #f97316; }}
        .bar-fill.medium {{ background: #eab308; }}
        .bar-fill.low {{ background: #22c55e; }}
        .bar-fill.info {{ background: #3b82f6; }}
        .findings-table {{ width: 100%; border-collapse: collapse; }}
        .findings-table th {{ text-align: left; padding: 12px 16px; background: #334155;
                             font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
                             color: #94a3b8; }}
        .findings-table td {{ padding: 12px 16px; border-bottom: 1px solid #334155;
                             font-size: 14px; }}
        .findings-table tr:hover {{ background: #1e293b; }}
        .severity-tag {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
                        font-size: 11px; font-weight: 600; text-transform: uppercase; }}
        .severity-tag.critical {{ background: rgba(239,68,68,0.2); color: #ef4444; }}
        .severity-tag.high {{ background: rgba(249,115,22,0.2); color: #f97316; }}
        .severity-tag.medium {{ background: rgba(234,179,8,0.2); color: #eab308; }}
        .severity-tag.low {{ background: rgba(34,197,94,0.2); color: #22c55e; }}
        .severity-tag.info {{ background: rgba(59,130,246,0.2); color: #3b82f6; }}
        .finding-detail {{ display: none; padding: 16px; background: #0f172a;
                          border-radius: 8px; margin: 8px 0; font-size: 13px; }}
        .finding-detail.show {{ display: block; }}
        .finding-detail pre {{ background: #1e293b; padding: 12px; border-radius: 6px;
                              overflow-x: auto; font-size: 12px; color: #a5b4fc; }}
        .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 32px;
                   padding: 16px; border-top: 1px solid #334155; }}
        .nav {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
        .nav button {{ background: #334155; border: 1px solid #475569; color: #e2e8f0;
                      padding: 8px 16px; border-radius: 6px; cursor: pointer;
                      font-size: 13px; }}
        .nav button:hover {{ background: #475569; }}
        .nav button.active {{ background: #6366f1; border-color: #6366f1; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Vulnerability Scan Report</h1>
            <div class="meta">
                <span>🎯 Target: <strong>{result.target}</strong></span>
                <span>🔬 Scanner: <strong>{result.scanner.upper()}</strong></span>
                <span>📋 Type: <strong>{result.scan_type}</strong></span>
                <span>🆔 Scan ID: <strong>{result.scan_id[:16]}...</strong></span>
            </div>
            <div style="margin-top: 12px;" class="meta">
                <span>⏱ Started: {result.start_time}</span>
                <span>⏱ Ended: {result.end_time}</span>
                <span>⌛ Duration: {result.duration_seconds:.1f}s</span>
            </div>
        </div>

        <div class="summary-cards">
            <div class="card total">
                <div class="count">{result.total_findings}</div>
                <div class="label">Total Findings</div>
            </div>
            <div class="card critical">
                <div class="count">{result.critical_count}</div>
                <div class="label">Critical</div>
            </div>
            <div class="card high">
                <div class="count">{result.high_count}</div>
                <div class="label">High</div>
            </div>
            <div class="card medium">
                <div class="count">{result.medium_count}</div>
                <div class="label">Medium</div>
            </div>
            <div class="card low">
                <div class="count">{result.low_count}</div>
                <div class="label">Low</div>
            </div>
            <div class="card info">
                <div class="count">{result.info_count}</div>
                <div class="label">Info</div>
            </div>
        </div>

        <div style="text-align: center; margin-bottom: 24px;">
            <span class="risk-badge risk-{risk_level.lower()}">{risk_level} Risk (Score: {risk_score}/100)</span>
        </div>

        <div class="severity-section">
            <h2>📊 Severity Distribution</h2>
            {severity_bars}
        </div>

        <div class="severity-section">
            <h2>🔎 Findings ({result.total_findings})</h2>
            <table class="findings-table">
                <thead>
                    <tr>
                        <th>Severity</th>
                        <th>Title</th>
                        <th>Endpoint</th>
                        <th>Category</th>
                        <th>CVE</th>
                    </tr>
                </thead>
                <tbody>
                    {findings_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated by QA-Framework Vulnerability Scanner | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
    </div>

    <script>
        document.querySelectorAll('.findings-table tbody tr').forEach(row => {{
            row.addEventListener('click', function() {{
                const detail = this.nextElementSibling;
                if (detail && detail.classList.contains('finding-detail')) {{
                    detail.classList.toggle('show');
                }}
            }});
        }});
    </script>
</body>
</html>"""

        with open(report_path, "w") as f:
            f.write(html)

        logger.info(f"HTML report generated: {report_path}")
        return str(report_path)

    def generate_markdown(self, result: VulnScanResult, filename: Optional[str] = None) -> str:
        """Generate Markdown vulnerability report.

        Args:
            result: VulnScanResult to format
            filename: Optional custom filename

        Returns:
            Path to the generated report file
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"vuln_report_{result.scanner}_{timestamp}.md"

        report_path = self.output_dir / filename

        risk_level, risk_score = self._calculate_risk(result)

        md = f"""# 🔍 Vulnerability Scan Report

**Target:** `{result.target}` | **Scanner:** {result.scanner.upper()} | **Type:** {result.scan_type}
**Scan ID:** `{result.scan_id[:16]}...` | **Duration:** {result.duration_seconds:.1f}s

---

## 📊 Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {result.critical_count} |
| 🟠 High | {result.high_count} |
| 🟡 Medium | {result.medium_count} |
| 🟢 Low | {result.low_count} |
| 🔵 Info | {result.info_count} |
| **Total** | **{result.total_findings}** |

**Risk Level: {risk_level}** (Score: {risk_score}/100)

---

## 🔎 Findings

"""

        if not result.findings:
            md += "_No vulnerabilities found._\n"
        else:
            for i, f in enumerate(result.findings, 1):
                severity_icon = {
                    VulnSeverity.CRITICAL: "🔴",
                    VulnSeverity.HIGH: "🟠",
                    VulnSeverity.MEDIUM: "🟡",
                    VulnSeverity.LOW: "🟢",
                    VulnSeverity.INFO: "🔵",
                }.get(f.severity, "⚪")

                md += f"### {i}. {severity_icon} {f.title}\n\n"
                md += f"- **Severity:** `{f.severity.value}`\n"
                md += f"- **Category:** {f.category.value}\n"
                md += f"- **Target:** `{f.target}`\n"
                if f.endpoint:
                    md += f"- **Endpoint:** `{f.endpoint}`\n"
                if f.method:
                    md += f"- **Method:** `{f.method}`\n"
                if f.port:
                    md += f"- **Port:** `{f.port}`\n"
                if f.cve_id:
                    md += f"- **CVE:** [{f.cve_id}](https://nvd.nist.gov/vuln/detail/{f.cve_id})\n"
                if f.cvss_score is not None:
                    md += f"- **CVSS:** {f.cvss_score}\n"

                md += f"\n**Description:** {f.description}\n\n"

                if f.evidence:
                    md += f"**Evidence:**\n```\n{f.evidence[:500]}\n```\n\n"
                if f.remediation:
                    md += f"**Remediation:** {f.remediation}\n\n"
                if f.references:
                    md += "**References:**\n"
                    for ref in f.references:
                        md += f"- {ref}\n"
                    md += "\n"

                md += "---\n\n"

        md += f"\n*Report generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"

        with open(report_path, "w") as f:
            f.write(md)

        logger.info(f"Markdown report generated: {report_path}")
        return str(report_path)

    def generate_all(self, result: VulnScanResult, base_name: Optional[str] = None) -> Dict[str, str]:
        """Generate all report formats.

        Args:
            result: VulnScanResult to report
            base_name: Base filename (without extension)

        Returns:
            Dict with format -> path mappings
        """
        if base_name is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_target = result.target.replace("://", "_").replace("/", "_")[:32]
            base_name = f"vuln_{result.scanner}_{safe_target}_{timestamp}"

        paths = {
            "json": self.generate_json(result, f"{base_name}.json"),
            "html": self.generate_html(result, f"{base_name}.html"),
            "md": self.generate_markdown(result, f"{base_name}.md"),
        }
        return paths

    # --- Private helpers ---

    def _render_severity_bars(self, result: VulnScanResult) -> str:
        """Render severity distribution bars as HTML."""
        total = max(result.total_findings, 1)
        bars = ""

        severities = [
            ("critical", "🔴 Critical", result.critical_count, "#ef4444"),
            ("high", "🟠 High", result.high_count, "#f97316"),
            ("medium", "🟡 Medium", result.medium_count, "#eab308"),
            ("low", "🟢 Low", result.low_count, "#22c55e"),
            ("info", "🔵 Info", result.info_count, "#3b82f6"),
        ]

        for key, label, count, _ in severities:
            pct = (count / total) * 100
            bars += f"""<div class="bar-container">
                <div class="bar-label">
                    <span>{label}</span>
                    <span>{count} ({pct:.1f}%)</span>
                </div>
                <div class="bar">
                    <div class="bar-fill {key}" style="width: {pct}%"></div>
                </div>
            </div>"""
        return bars

    def _render_findings_table(self, findings: List[VulnerabilityFinding]) -> str:
        """Render findings table rows as HTML."""
        rows = ""
        for f in findings:
            severity_class = f.severity.value.lower()
            cve_display = f.cve_id if f.cve_id else "-"
            category_display = f.category.value.replace("-", " ").title()

            evidence_html = ""
            if f.evidence or f.remediation:
                evidence_parts = []
                if f.evidence:
                    evidence_parts.append(
                        f"<strong>Evidence:</strong><pre>{self._escape_html(f.evidence[:300])}</pre>"
                    )
                if f.remediation:
                    evidence_parts.append(
                        f"<strong>Remediation:</strong> {self._escape_html(f.remediation[:200])}"
                    )
                evidence_html = f'<div class="finding-detail">{"".join(evidence_parts)}</div>'

            rows += f"""<tr>
                    <td><span class="severity-tag {severity_class}">{f.severity.value}</span></td>
                    <td>{self._escape_html(f.title[:80])}</td>
                    <td><code>{self._escape_html(f.endpoint[:50] or "-")}</code></td>
                    <td>{category_display}</td>
                    <td>{cve_display}</td>
                </tr>{evidence_html}"""
        return rows

    @staticmethod
    def _calculate_risk(result: VulnScanResult):
        """Calculate risk level and score."""
        risk_score = (
            result.critical_count * 10
            + result.high_count * 7
            + result.medium_count * 4
            + result.low_count * 1
        )
        if result.total_findings > 0:
            risk_score = min(100, (risk_score / (result.total_findings * 10)) * 100)
        else:
            risk_score = 0

        if risk_score >= 75:
            risk_level = "Critical"
        elif risk_score >= 50:
            risk_level = "High"
        elif risk_score >= 25:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return risk_level, round(risk_score, 1)

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML entities."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
