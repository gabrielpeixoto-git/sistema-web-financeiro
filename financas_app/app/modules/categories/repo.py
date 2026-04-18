from __future__ import annotations

from sqlmodel import Session, select

from financas_app.app.modules.categories.models import Category


def list_categories(session: Session, user_id: int) -> list[Category]:
    return list(session.exec(select(Category).where(Category.user_id == user_id).order_by(Category.id)))


def get_category(session: Session, user_id: int, category_id: int) -> Category | None:
    return session.exec(
        select(Category).where(Category.user_id == user_id, Category.id == category_id)
    ).first()


def get_category_by_name(session: Session, user_id: int, name: str) -> Category | None:
    return session.exec(
        select(Category).where(Category.user_id == user_id, Category.name == name.strip())
    ).first()


def add(session: Session, c: Category) -> None:
    session.add(c)

