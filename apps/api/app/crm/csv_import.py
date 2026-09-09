from __future__ import annotations

import csv
from io import StringIO

from pydantic import ValidationError

from app.crm.normalization import normalize_domain
from app.crm.schemas import AccountCreate, CsvParseResult, CsvPreviewRow

ACCOUNT_CSV_FIELDS = {
    "name",
    "domain",
    "website",
    "industry",
    "company_size",
    "country",
    "city",
    "account_type",
    "source",
    "owner_id",
    "status",
    "lead_score",
    "notes",
}


def _clean_row(row: dict[str | None, str | None]) -> dict[str, object]:
    cleaned: dict[str, object] = {}
    for key, value in row.items():
        if key is None or value is None:
            continue
        stripped = value.strip()
        if stripped:
            cleaned[key.strip()] = stripped
    return cleaned


def parse_account_csv(content: str, *, max_rows: int = 5_000) -> CsvParseResult:
    reader = csv.DictReader(StringIO(content.lstrip("\ufeff")))
    headers = {header.strip() for header in (reader.fieldnames or []) if header}
    file_errors: list[str] = []
    if "name" not in headers:
        file_errors.append("CSV must contain a name column")
    unknown = sorted(headers - ACCOUNT_CSV_FIELDS)
    if unknown:
        file_errors.append(f"Unknown columns: {', '.join(unknown)}")

    source_rows = list(reader)
    if len(source_rows) > max_rows:
        return CsvParseResult(
            rows=[],
            valid_rows=0,
            invalid_rows=len(source_rows),
            file_errors=[f"CSV exceeds the maximum of {max_rows} data rows"],
        )

    seen_domains: set[str] = set()
    rows: list[CsvPreviewRow] = []
    for row_number, raw in enumerate(source_rows, start=2):
        values = _clean_row(raw)
        errors: list[str] = []
        normalized_domain = normalize_domain(str(values["domain"])) if "domain" in values else None
        if normalized_domain is not None:
            if normalized_domain in seen_domains:
                errors.append("duplicate domain in file")
            seen_domains.add(normalized_domain)
        try:
            AccountCreate.model_validate(values)
        except ValidationError as exc:
            errors.extend(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors()
            )
        rows.append(
            CsvPreviewRow(
                row_number=row_number,
                values=values,
                normalized_domain=normalized_domain,
                valid=not errors,
                errors=errors,
            )
        )
    return CsvParseResult(
        rows=rows,
        valid_rows=sum(row.valid for row in rows),
        invalid_rows=sum(not row.valid for row in rows),
        file_errors=file_errors,
    )
