"""
Risk Analyzer Module
Analyze detection risk for modified documents

Author: DevNoLife
Version: 1.0
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import docx
from dataclasses import dataclass


@dataclass
class RiskScore:
    """Risk score data class"""
    overall_score: float  # 0-100, lower is better
    unicode_density: float
    invisible_char_density: float
    modification_count: int
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    warnings: List[str]
    recommendations: List[str]


class RiskAnalyzer:
    """Analyze detection risk for modified documents"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_document(self, doc_path: str, changes_log: Dict[str, Any] = None) -> RiskScore:
        """
        Analyze detection risk for a document

        Args:
            doc_path: Path to DOCX file
            changes_log: Optional change log from processing

        Returns:
            RiskScore object with detailed analysis
        """
        self.logger.info(f"Analyzing detection risk for: {doc_path}")

        try:
            doc = docx.Document(doc_path)
        except Exception as e:
            self.logger.error(f"Failed to load document: {e}")
            return RiskScore(
                overall_score=100.0,
                unicode_density=0.0,
                invisible_char_density=0.0,
                modification_count=0,
                risk_level="CRITICAL",
                warnings=[f"Failed to load document: {e}"],
                recommendations=["Check document integrity"]
            )

        # Analyze document content
        unicode_count, invisible_count, total_chars = self._analyze_content(doc)

        # Get modification count from changes log
        modification_count = 0
        if changes_log and 'statistics' in changes_log:
            modification_count = changes_log['statistics'].get('total_changes', 0)

        # Calculate densities
        unicode_density = (unicode_count / total_chars * 100) if total_chars > 0 else 0
        invisible_density = (invisible_count / total_chars * 100) if total_chars > 0 else 0

        # Calculate overall risk score
        risk_score, risk_level, warnings, recommendations = self._calculate_risk(
            unicode_density, invisible_density, modification_count
        )

        self.logger.info(f"Risk analysis complete: {risk_level} ({risk_score:.1f}/100)")

        return RiskScore(
            overall_score=risk_score,
            unicode_density=unicode_density,
            invisible_char_density=invisible_density,
            modification_count=modification_count,
            risk_level=risk_level,
            warnings=warnings,
            recommendations=recommendations
        )

    def _analyze_content(self, doc) -> tuple:
        """Analyze document content for unicode and invisible characters"""
        unicode_count = 0
        invisible_count = 0
        total_chars = 0

        # Known Cyrillic/Greek lookalikes
        cyrillic_chars = set('АВСЕНІЈКМНОРЅТХҮаcеіјорѕху')
        greek_chars = set('ΑΒΕΗΙΚΜΝΟΡΤΧΥΖαοpρχυ')

        # Zero-width and invisible characters
        invisible_chars = set('\u200B\u200C\u200D\uFEFF\u2060\u180E\u2061\u2062\u2063\u2064')

        for paragraph in doc.paragraphs:
            text = paragraph.text
            total_chars += len(text)

            for char in text:
                if char in cyrillic_chars or char in greek_chars:
                    unicode_count += 1
                elif char in invisible_chars:
                    invisible_count += 1

        return unicode_count, invisible_count, total_chars

    def _calculate_risk(self, unicode_density: float, invisible_density: float,
                       modification_count: int) -> tuple:
        """
        Calculate overall risk score based on metrics

        Returns:
            (risk_score, risk_level, warnings, recommendations)
        """
        warnings = []
        recommendations = []

        # Base risk score from densities
        # Unicode substitution: higher density = higher risk
        unicode_risk = min(unicode_density * 10, 50)  # Max 50 points

        # Invisible characters: higher density = higher risk
        invisible_risk = min(invisible_density * 15, 30)  # Max 30 points

        # Modification count: more changes = higher risk
        mod_risk = min(modification_count * 0.2, 20)  # Max 20 points

        overall_score = unicode_risk + invisible_risk + mod_risk

        # Determine risk level
        if overall_score < 20:
            risk_level = "LOW"
        elif overall_score < 40:
            risk_level = "MEDIUM"
        elif overall_score < 60:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # Generate warnings
        if unicode_density > 5:
            warnings.append(f"High unicode substitution density ({unicode_density:.2f}%)")
        if invisible_density > 3:
            warnings.append(f"High invisible character density ({invisible_density:.2f}%)")
        if modification_count > 100:
            warnings.append(f"Large number of modifications ({modification_count})")

        # Generate recommendations
        if risk_level in ["HIGH", "CRITICAL"]:
            recommendations.append("Consider using 'stealth' mode for lower detection risk")
            recommendations.append("Review modifications manually for patterns")

        if unicode_density > 5:
            recommendations.append("Reduce unicode substitution rate in config")

        if invisible_density > 3:
            recommendations.append("Reduce invisible character insertion rate")

        if modification_count > 150:
            recommendations.append("Consider processing document in multiple passes")

        if not warnings:
            recommendations.append("Risk level is acceptable for submission")

        return overall_score, risk_level, warnings, recommendations

    def generate_report(self, risk_score: RiskScore, output_path: str = None) -> str:
        """
        Generate a human-readable risk report

        Args:
            risk_score: RiskScore object
            output_path: Optional path to save report

        Returns:
            Report as string
        """
        report_lines = [
            "=" * 70,
            "DETECTION RISK ANALYSIS REPORT",
            "=" * 70,
            "",
            f"Overall Risk Score: {risk_score.overall_score:.1f}/100",
            f"Risk Level: {risk_score.risk_level}",
            "",
            "Metrics:",
            f"  - Unicode Substitution Density: {risk_score.unicode_density:.2f}%",
            f"  - Invisible Character Density: {risk_score.invisible_char_density:.2f}%",
            f"  - Total Modifications: {risk_score.modification_count}",
            "",
        ]

        if risk_score.warnings:
            report_lines.append("⚠️  Warnings:")
            for warning in risk_score.warnings:
                report_lines.append(f"  - {warning}")
            report_lines.append("")

        if risk_score.recommendations:
            report_lines.append("💡 Recommendations:")
            for rec in risk_score.recommendations:
                report_lines.append(f"  - {rec}")
            report_lines.append("")

        # Risk level interpretation
        risk_interpretation = {
            "LOW": "✅ Low detection risk - Safe for submission",
            "MEDIUM": "⚠️  Medium risk - Review modifications before submission",
            "HIGH": "🔴 High risk - Consider reducing modifications",
            "CRITICAL": "⛔ Critical risk - Not recommended for submission"
        }

        report_lines.append("Interpretation:")
        report_lines.append(f"  {risk_interpretation.get(risk_score.risk_level, 'Unknown')}")
        report_lines.append("")
        report_lines.append("=" * 70)

        report = "\n".join(report_lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            self.logger.info(f"Risk report saved to: {output_path}")

        return report
