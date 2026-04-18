from __future__ import annotations

import csv
import io
import uuid
from collections import defaultdict
from datetime import date

from sqlmodel import Session

from financas_app.app.common.money import parse_brl_to_cents
from financas_app.app.modules.accounts.repo import get_account, get_account_by_name
from financas_app.app.modules.audit.service import log_action
from financas_app.app.modules.categories.repo import get_category, get_category_by_name
from financas_app.app.modules.transactions import repo
from financas_app.app.modules.transactions.models import Transaction

_IMPORT_SKIP_SAMPLE_LIMIT = 20


def _note_skip(
    reasons: defaultdict[str, int],
    samples: list[dict[str, int | str]],
    *,
    reason: str,
    line_no: int,
) -> None:
    reasons[reason] += 1
    if len(samples) < _IMPORT_SKIP_SAMPLE_LIMIT:
        samples.append({"line": line_no, "reason": reason})


def create_transaction(
    session: Session,
    *,
    user_id: int,
    account_id: int,
    kind: str,
    amount: str,
    occurred_on: date,
    category_id: int | None = None,
    description: str = "",
) -> Transaction:
    if kind not in ("in", "out"):
        raise ValueError("invalid kind")
    if not get_account(session, user_id, account_id):
        raise ValueError("invalid account")
    if category_id is not None and not get_category(session, user_id, category_id):
        raise ValueError("invalid category")
    amount_cents = parse_brl_to_cents(amount)
    if amount_cents <= 0:
        raise ValueError("amount must be > 0")

    t = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        kind=kind,
        amount_cents=amount_cents,
        occurred_on=occurred_on,
        description=(description or "").strip(),
    )
    repo.add(session, t)
    session.commit()
    session.refresh(t)
    log_action(
        session,
        user_id=user_id,
        action="transactions.create",
        entity="transaction",
        entity_id=t.id,
        detail=f"kind={kind};amount_cents={amount_cents}",
    )
    return t


def create_transfer(
    session: Session,
    *,
    user_id: int,
    from_account_id: int,
    to_account_id: int,
    amount: str,
    occurred_on: date,
    description: str = "",
) -> tuple[Transaction, Transaction]:
    if from_account_id == to_account_id:
        raise ValueError("same account")
    from_acc = get_account(session, user_id, from_account_id)
    to_acc = get_account(session, user_id, to_account_id)
    if not from_acc or not to_acc:
        raise ValueError("invalid account")
    amount_cents = parse_brl_to_cents(amount)
    if amount_cents <= 0:
        raise ValueError("amount must be > 0")
    if balance_for_account(session, user_id=user_id, account_id=from_account_id) < amount_cents:
        raise ValueError("insufficient balance")

    gid = uuid.uuid4().hex
    base = (description or "").strip()
    d_out = f"→ {to_acc.name}" + (f" — {base}" if base else "")
    d_in = f"← {from_acc.name}" + (f" — {base}" if base else "")
    if len(d_out) > 200:
        d_out = d_out[:200]
    if len(d_in) > 200:
        d_in = d_in[:200]

    t_out = Transaction(
        user_id=user_id,
        account_id=from_account_id,
        category_id=None,
        kind="out",
        amount_cents=amount_cents,
        occurred_on=occurred_on,
        description=d_out,
        transfer_group_id=gid,
    )
    t_in = Transaction(
        user_id=user_id,
        account_id=to_account_id,
        category_id=None,
        kind="in",
        amount_cents=amount_cents,
        occurred_on=occurred_on,
        description=d_in,
        transfer_group_id=gid,
    )
    repo.add(session, t_out)
    repo.add(session, t_in)
    session.commit()
    session.refresh(t_out)
    session.refresh(t_in)
    log_action(
        session,
        user_id=user_id,
        action="transactions.transfer",
        entity="transaction",
        entity_id=t_out.id,
        detail=f"group={gid};cents={amount_cents}",
    )
    return t_out, t_in


def list_transactions(session: Session, *, user_id: int, limit: int = 50) -> list[Transaction]:
    return repo.list_transactions(session, user_id, limit=limit)


def balance_for_account(session: Session, *, user_id: int, account_id: int) -> int:
    return repo.balance_for_account(session, user_id, account_id)


def balance_total(session: Session, *, user_id: int) -> int:
    return repo.balance_total(session, user_id)


def export_csv(
    session: Session,
    *,
    user_id: int,
    start: date | None = None,
    end: date | None = None,
) -> str:
    from financas_app.app.modules.accounts.repo import get_account
    from financas_app.app.modules.categories.repo import get_category

    txs = repo.list_transactions(session, user_id, limit=100000)
    out = io.StringIO()
    writer = csv.writer(out)
    # User-friendly format matching import requirements
    writer.writerow(["date", "kind", "account_name", "category_name", "amount", "description"])
    for t in txs:
        if start and t.occurred_on < start:
            continue
        if end and t.occurred_on > end:
            continue
        # Get account and category names
        acc = get_account(session, user_id, t.account_id)
        cat_name = ""
        if t.category_id:
            cat = get_category(session, user_id, t.category_id)
            cat_name = cat.name if cat else ""
        # Format amount in BRL
        amount_brl = f"{t.amount_cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        writer.writerow(
            [
                t.occurred_on.isoformat(),
                t.kind,
                acc.name if acc else "",
                cat_name,
                amount_brl,
                t.description or "",
            ]
        )
    return out.getvalue()


def import_csv_content(
    session: Session, *, user_id: int, content: str
) -> dict[str, int | dict[str, int] | list[dict[str, int | str]]]:
    reader = csv.DictReader(io.StringIO(content))
    created = 0
    skipped = 0
    reasons: defaultdict[str, int] = defaultdict(int)
    samples: list[dict[str, int | str]] = []
    for row in reader:
        line_no = reader.line_num
        try:
            kind = (row.get("kind") or "").strip()
            occurred_on = date.fromisoformat((row.get("date") or "").strip())
            account_name = (row.get("account_name") or "").strip()
            category_name = (row.get("category_name") or "").strip()
            amount = (row.get("amount") or "").strip()
            description = (row.get("description") or "").strip()

            if kind not in ("in", "out"):
                skipped += 1
                _note_skip(reasons, samples, reason="invalid_kind", line_no=line_no)
                continue
            acc = get_account_by_name(session, user_id, account_name)
            if not acc:
                skipped += 1
                _note_skip(reasons, samples, reason="account_not_found", line_no=line_no)
                continue
            cat_id = None
            if category_name:
                cat = get_category_by_name(session, user_id, category_name)
                if not cat:
                    skipped += 1
                    _note_skip(reasons, samples, reason="category_not_found", line_no=line_no)
                    continue
                cat_id = cat.id
            amount_cents = parse_brl_to_cents(amount)
            if amount_cents <= 0:
                skipped += 1
                _note_skip(reasons, samples, reason="invalid_amount", line_no=line_no)
                continue
            if repo.exists_duplicate(
                session,
                user_id=user_id,
                account_id=acc.id,
                category_id=cat_id,
                kind=kind,
                amount_cents=amount_cents,
                occurred_on=occurred_on,
                description=description,
            ):
                skipped += 1
                _note_skip(reasons, samples, reason="duplicate", line_no=line_no)
                continue
            create_transaction(
                session,
                user_id=user_id,
                account_id=acc.id,
                kind=kind,
                amount=amount,
                occurred_on=occurred_on,
                category_id=cat_id,
                description=description,
            )
            created += 1
        except Exception:
            skipped += 1
            _note_skip(reasons, samples, reason="row_error", line_no=line_no)
    log_action(
        session,
        user_id=user_id,
        action="transactions.import_csv",
        entity="transaction",
        detail=f"created={created};skipped={skipped}",
    )
    return {
        "created": created,
        "skipped": skipped,
        "skip_reasons": dict(reasons),
        "skip_samples": samples,
    }

