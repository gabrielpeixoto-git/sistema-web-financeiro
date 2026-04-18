from __future__ import annotations

import csv
import io

from sqlmodel import Session, create_engine

from financas_app.app.common.tasks import set_task
from financas_app.app.modules.transactions import service

_IMPORT_REQUIRED_COLUMNS = frozenset(
    {"date", "kind", "account_name", "category_name", "amount", "description"}
)


class ImportCsvValidationError(Exception):
    def __init__(self, *, code: str, detail: str, missing_columns: list[str] | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.missing_columns = list(missing_columns or [])


def read_import_csv_strict(*, filename: str | None, raw: bytes) -> str:
    if not filename or not filename.lower().endswith(".csv"):
        raise ImportCsvValidationError(
            code="invalid_file_extension",
            detail="Envie um arquivo com extensão .csv.",
        )
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ImportCsvValidationError(
            code="invalid_csv_encoding",
            detail="O arquivo deve estar codificado em UTF-8.",
        ) from e
    header = next(csv.reader(io.StringIO(content)), None)
    present = set(header) if header else set()
    missing = sorted(_IMPORT_REQUIRED_COLUMNS - present)
    if not header or missing:
        raise ImportCsvValidationError(
            code="invalid_csv_header",
            detail="Cabeçalho do CSV incompleto. Colunas obrigatórias: "
            + ", ".join(sorted(_IMPORT_REQUIRED_COLUMNS))
            + ".",
            missing_columns=missing,
        )
    return content


def run_import_csv_task(task_id: str, *, user_id: int, content: str, db_url: str) -> None:
    set_task(task_id, status="running")
    try:
        engine = create_engine(db_url, echo=False)
        with Session(engine) as session:
            r = service.import_csv_content(session, user_id=user_id, content=content)
        sr = r.get("skip_reasons") or {}
        reason_part = ""
        if sr:
            reason_part = " " + ";".join(f"{k}:{v}" for k, v in sorted(sr.items()) if v)
        set_task(
            task_id,
            status="done",
            detail=f"created={r['created']} skipped={r['skipped']}{reason_part}",
            meta={
                "created": r["created"],
                "skipped": r["skipped"],
                "skip_reasons": sr,
                "skip_samples": r.get("skip_samples") or [],
            },
        )
    except Exception as e:
        set_task(task_id, status="error", detail=str(e))
