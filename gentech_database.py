"""
Database integration for GeneTech genetic part availability checks.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests


BASE_DIR = Path(__file__).resolve().parent
CIRCUITS_FILE = BASE_DIR / "circuits.txt"
PART_MAPPINGS_FILE = BASE_DIR / "part_mappings.csv"
REPORTS_DIR = BASE_DIR / "database_reports"
REPORTS_DIR.mkdir(exist_ok=True)


@dataclass
class PartAvailability:
    part: str
    part_type: str
    registry_id: Optional[str]
    registry_name: Optional[str]
    available: bool
    source: str
    description: str = ""
    url: str = ""
    reason: str = ""

    def to_legacy_dict(self) -> dict:
        payload = {
            "part": self.part,
            "type": self.part_type,
            "available": self.available,
            "reason": self.reason,
        }
        if self.registry_id:
            payload["igem_id"] = self.registry_id
        if self.url:
            payload["url"] = self.url
        if self.description:
            payload["description"] = self.description
        payload["source"] = self.source
        payload["registry_name"] = self.registry_name
        return payload


class PartMapper:
    """
    Maps GeneTech parts to canonical registry identifiers.
    """

    DEFAULT_PARTS = {
        "PTac": {
            "registry_id": "BBa_K864500",
            "part_type": "promoter",
            "description": "Tac promoter",
        },
        "PTet": {
            "registry_id": "BBa_R0040",
            "part_type": "promoter",
            "description": "TetR repressible promoter",
        },
        "PBad": {
            "registry_id": "BBa_I0500",
            "part_type": "promoter",
            "description": "Arabinose promoter",
        },
        "PAmtR": {
            "registry_id": "BBa_K1372007",
            "part_type": "promoter",
            "description": "AmtR repressible promoter",
        },
        "PAmeR": {
            "registry_id": "BBa_K1372008",
            "part_type": "promoter",
            "description": "AmeR repressible promoter",
        },
        "PHlYllR": {
            "registry_id": "BBa_K1372009",
            "part_type": "promoter",
            "description": "HlyIIR repressible promoter",
        },
        "PSrpR": {
            "registry_id": "BBa_K1372010",
            "part_type": "promoter",
            "description": "SrpR repressible promoter",
        },
        "PPhlF": {
            "registry_id": "BBa_K1372011",
            "part_type": "promoter",
            "description": "PhlF repressible promoter",
        },
        "PBM3R1": {
            "registry_id": "BBa_K1372012",
            "part_type": "promoter",
            "description": "BM3R1 repressible promoter",
        },
        "PBetl": {
            "registry_id": "BBa_K1372013",
            "part_type": "promoter",
            "description": "BetI repressible promoter",
        },
        "AmtR": {
            "registry_id": "BBa_K1372001",
            "part_type": "cds",
            "description": "AmtR repressor",
        },
        "AmeR": {
            "registry_id": "BBa_K1372002",
            "part_type": "cds",
            "description": "AmeR repressor",
        },
        "HlYllR": {
            "registry_id": "BBa_K1372003",
            "part_type": "cds",
            "description": "HlyIIR repressor",
        },
        "SrpR": {
            "registry_id": "BBa_K1372004",
            "part_type": "cds",
            "description": "SrpR repressor",
        },
        "PhlF": {
            "registry_id": "BBa_K1372005",
            "part_type": "cds",
            "description": "PhlF repressor",
        },
        "BM3R1": {
            "registry_id": "BBa_K1372006",
            "part_type": "cds",
            "description": "BM3R1 repressor",
        },
        "Betl": {
            "registry_id": "BBa_K1372014",
            "part_type": "cds",
            "description": "BetI repressor",
        },
        "YFP": {
            "registry_id": "BBa_E0030",
            "part_type": "reporter",
            "description": "YFP reporter",
        },
        "ECK120033737": {
            "registry_id": "BBa_B0015",
            "part_type": "terminator",
            "description": "Double terminator",
        },
    }

    DEFAULT_RBS_ID = "BBa_B0034"

    def __init__(self, csv_path: Path = PART_MAPPINGS_FILE):
        self.csv_path = Path(csv_path)
        self.mapping: Dict[str, dict] = {}
        self._load_defaults()
        self._load_from_csv()

    def _load_defaults(self):
        self.mapping = {part: info.copy() for part, info in self.DEFAULT_PARTS.items()}
        for rbs in ["A1", "F1", "H1", "S1", "P1", "B1", "E1"]:
            self.mapping[rbs] = {
                "registry_id": self.DEFAULT_RBS_ID,
                "part_type": "rbs",
                "description": "Ribosome binding site",
            }

    def _load_from_csv(self):
        if not self.csv_path.exists():
            return

        try:
            with self.csv_path.open("r", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    part = row.get("genetech_part", "").strip()
                    registry_id = row.get("igem_id", "").strip()
                    if not part or not registry_id:
                        continue
                    self.mapping[part] = {
                        "registry_id": registry_id,
                        "part_type": row.get("type", "").strip() or self.get_part_type(part),
                        "description": row.get("description", "").strip(),
                    }
        except Exception:
            # Fall back to baked-in mappings if the CSV is malformed.
            pass

    def get_registry_id(self, part: str) -> Optional[str]:
        entry = self.mapping.get(part)
        return entry.get("registry_id") if entry else None

    def get_igem_id(self, part: str) -> Optional[str]:
        return self.get_registry_id(part)

    def get_part_type(self, part: str) -> str:
        entry = self.mapping.get(part)
        if entry and entry.get("part_type"):
            return entry["part_type"]
        if part.startswith("P") and part != "YFP":
            return "promoter"
        if part in {"AmtR", "AmeR", "HlYllR", "SrpR", "PhlF", "BM3R1", "Betl"}:
            return "cds"
        if part == "YFP":
            return "reporter"
        if part in {"A1", "F1", "H1", "S1", "P1", "B1", "E1"}:
            return "rbs"
        if part == "ECK120033737":
            return "terminator"
        return "unknown"

    def get_part_info(self, part: str) -> dict:
        info = self.mapping.get(part, {}).copy()
        info.setdefault("part_type", self.get_part_type(part))
        return info


class RegistryProvider:
    name = "Registry"

    def lookup(self, registry_id: str) -> dict:
        raise NotImplementedError


class IGEMRegistryProvider(RegistryProvider):
    name = "iGEM Registry"

    KNOWN_PARTS = {
        "BBa_R0040": "TetR repressible promoter",
        "BBa_J23100": "Constitutive promoter",
        "BBa_B0034": "RBS (Elowitz 1999)",
        "BBa_E0030": "YFP reporter",
        "BBa_B0015": "Double terminator",
        "BBa_C0012": "LacI repressor",
        "BBa_K864500": "Tac promoter",
        "BBa_I0500": "AraC regulated promoter",
        "BBa_K1372001": "AmtR repressor",
        "BBa_K1372002": "AmeR repressor",
        "BBa_K1372003": "HlyIIR repressor",
        "BBa_K1372004": "SrpR repressor",
        "BBa_K1372005": "PhlF repressor",
        "BBa_K1372006": "BM3R1 repressor",
        "BBa_K1372007": "AmtR repressible promoter",
        "BBa_K1372008": "AmeR repressible promoter",
        "BBa_K1372009": "HlyIIR repressible promoter",
        "BBa_K1372010": "SrpR repressible promoter",
        "BBa_K1372011": "PhlF repressible promoter",
        "BBa_K1372012": "BM3R1 repressible promoter",
        "BBa_K1372013": "BetI repressible promoter",
        "BBa_K1372014": "BetI repressor",
    }

    def __init__(self, allow_web_lookup: bool = False, timeout: int = 3):
        self.allow_web_lookup = allow_web_lookup
        self.timeout = timeout
        self.cache: Dict[str, dict] = {}

    def lookup(self, registry_id: str) -> dict:
        if registry_id in self.cache:
            return self.cache[registry_id]

        url = f"https://parts.igem.org/Part:{registry_id}"
        if registry_id in self.KNOWN_PARTS:
            result = {
                "found": True,
                "source": "local_catalog",
                "description": self.KNOWN_PARTS[registry_id],
                "url": url,
            }
        elif self.allow_web_lookup:
            try:
                response = requests.get(url, timeout=self.timeout)
                result = {
                    "found": response.status_code == 200 and "part_name" in response.text.lower(),
                    "source": "web",
                    "description": "",
                    "url": url,
                }
            except requests.RequestException:
                result = {
                    "found": False,
                    "source": "web_unreachable",
                    "description": "",
                    "url": url,
                }
        else:
            result = {
                "found": False,
                "source": "web_lookup_disabled",
                "description": "",
                "url": url,
            }

        self.cache[registry_id] = result
        return result


class BioPartsDBProvider(RegistryProvider):
    """
    Lightweight BioPartsDB-compatible adapter.

    This project currently maps parts through iGEM IDs, so this provider mainly
    exposes outbound links and a consistent integration point for future APIs.
    """

    name = "BioPartsDB"

    def lookup(self, registry_id: str) -> dict:
        url = f"https://biopartsdb.org/part/{registry_id}"
        return {
            "found": False,
            "source": "link_only",
            "description": "",
            "url": url,
        }


class GeneTechDatabase:
    """
    Integration layer used by the GUI and scripts to assess part availability
    and whether generated circuits are buildable from known registry parts.
    """

    def __init__(self, allow_web_lookup: bool = False, providers: Optional[List[RegistryProvider]] = None):
        self.mapper = PartMapper()
        self.providers = providers or [
            IGEMRegistryProvider(allow_web_lookup=allow_web_lookup),
            BioPartsDBProvider(),
        ]

    def check_circuits_file(self, filename: Path | str = CIRCUITS_FILE) -> List[dict]:
        report = self.analyze_circuits_file(filename)
        return [entry["availability"] for entry in report["parts"]]

    def analyze_circuits_file(self, filename: Path | str = CIRCUITS_FILE) -> dict:
        filename = Path(filename)
        if not filename.exists():
            raise FileNotFoundError(f"{filename} not found")

        circuits = self._parse_circuits_file(filename)
        unique_parts = sorted({part for circuit in circuits for part in circuit["parts"]})
        part_entries = [self._resolve_part(part) for part in unique_parts]
        part_lookup = {entry["part"]: entry for entry in part_entries}

        circuit_reports = []
        for circuit in circuits:
            missing = [part_lookup[part] for part in circuit["parts"] if not part_lookup[part]["availability"]["available"]]
            circuit_reports.append(
                {
                    "circuit_index": circuit["circuit_index"],
                    "parts": [part_lookup[part] for part in circuit["parts"]],
                    "buildable": len(missing) == 0,
                    "missing_parts": missing,
                }
            )

        summary = {
            "total_parts": len(part_entries),
            "available_parts": sum(1 for entry in part_entries if entry["availability"]["available"]),
            "missing_parts": sum(1 for entry in part_entries if not entry["availability"]["available"]),
            "total_circuits": len(circuit_reports),
            "buildable_circuits": sum(1 for report in circuit_reports if report["buildable"]),
            "all_circuits_buildable": all(report["buildable"] for report in circuit_reports) if circuit_reports else False,
        }

        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_file": str(filename),
            "providers": [provider.name for provider in self.providers],
            "summary": summary,
            "parts": part_entries,
            "circuits": circuit_reports,
        }
        report["report_file"] = self._save_report(report)
        return report

    def assess_buildability(self, filename: Path | str = CIRCUITS_FILE) -> bool:
        return self.analyze_circuits_file(filename)["summary"]["all_circuits_buildable"]

    def _resolve_part(self, part: str) -> dict:
        part_info = self.mapper.get_part_info(part)
        registry_id = part_info.get("registry_id")
        part_type = part_info.get("part_type", "unknown")
        description = part_info.get("description", "")

        if not registry_id:
            availability = PartAvailability(
                part=part,
                part_type=part_type,
                registry_id=None,
                registry_name=None,
                available=False,
                source="mapping",
                description=description,
                reason="No registry mapping",
            )
            provider_results = []
        else:
            provider_results = []
            availability = None
            for provider in self.providers:
                lookup = provider.lookup(registry_id)
                provider_result = {
                    "registry_name": provider.name,
                    "registry_id": registry_id,
                    "available": lookup.get("found", False),
                    "source": lookup.get("source", ""),
                    "description": lookup.get("description", ""),
                    "url": lookup.get("url", ""),
                }
                provider_results.append(provider_result)
                if provider_result["available"] and availability is None:
                    availability = PartAvailability(
                        part=part,
                        part_type=part_type,
                        registry_id=registry_id,
                        registry_name=provider.name,
                        available=True,
                        source=provider_result["source"],
                        description=provider_result["description"] or description,
                        url=provider_result["url"],
                    )

            if availability is None:
                primary = provider_results[0] if provider_results else {}
                availability = PartAvailability(
                    part=part,
                    part_type=part_type,
                    registry_id=registry_id,
                    registry_name=primary.get("registry_name"),
                    available=False,
                    source=primary.get("source", "registry"),
                    description=description,
                    url=primary.get("url", ""),
                    reason="Not found in configured registries",
                )

        return {
            "part": part,
            "part_type": part_type,
            "registry_id": registry_id,
            "description": description,
            "availability": availability.to_legacy_dict(),
            "providers": provider_results,
        }

    def _parse_circuits_file(self, filename: Path) -> List[dict]:
        content = filename.read_text()
        blocks = [block.strip() for block in content.split("*******************") if block.strip()]
        circuits = []

        for index, block in enumerate(blocks, start=1):
            lines = []
            parts = set()
            for raw_line in block.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("*") or line.startswith("Genetic Circuit"):
                    continue
                lines.append(line)
                parts.update(self._extract_parts_from_line(line))

            if lines:
                circuits.append(
                    {
                        "circuit_index": index,
                        "lines": lines,
                        "parts": sorted(parts),
                    }
                )

        return circuits

    def _extract_parts_from_line(self, line: str) -> Iterable[str]:
        cleaned = line
        for token in ["->", "|", "(", ")", "-", "^"]:
            cleaned = cleaned.replace(token, " ")

        ignored = {"and", "or", "not", "END"}
        for word in cleaned.split():
            candidate = word.strip()
            if not candidate or len(candidate) <= 1 or candidate.isdigit():
                continue
            if candidate in ignored:
                continue
            yield candidate

    def _save_report(self, report: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"igem_report_{timestamp}.json"
        report_path.write_text(json.dumps(report, indent=2))
        return str(report_path)


def check_current_circuits() -> List[dict]:
    return GeneTechDatabase().check_circuits_file()
