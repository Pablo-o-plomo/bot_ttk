from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Component, Dish, Ingredient


def create_dish(session: Session, user_id: int, title: str, final_yield: str) -> Dish:
    dish = Dish(user_id=user_id, title=title.strip(), final_yield=final_yield.strip())
    session.add(dish)
    session.commit()
    session.refresh(dish)
    return dish


def get_user_dishes(session: Session, user_id: int) -> list[Dish]:
    stmt = select(Dish).where(Dish.user_id == user_id).order_by(Dish.created_at.desc())
    return list(session.scalars(stmt).all())


def get_dish(session: Session, dish_id: int, user_id: int) -> Optional[Dish]:
    stmt = (
        select(Dish)
        .options(selectinload(Dish.components).selectinload(Component.ingredients))
        .where(Dish.id == dish_id, Dish.user_id == user_id)
    )
    return session.scalar(stmt)


def update_dish_text(session: Session, dish: Dish, field: str, value: str) -> Dish:
    setattr(dish, field, value.strip())
    session.add(dish)
    session.commit()
    session.refresh(dish)
    return dish


def set_dish_photo(session: Session, dish: Dish, original_path: str, processed_path: str | None) -> Dish:
    dish.photo_path = original_path
    dish.processed_photo_path = processed_path or ""
    session.add(dish)
    session.commit()
    session.refresh(dish)
    return dish


def add_component(
    session: Session,
    dish: Dish,
    portion_amount: str,
    name: str,
    component_yield: str,
    preparation_text: str,
) -> Component:
    sort_order = len(dish.components)
    component = Component(
        dish_id=dish.id,
        portion_amount=portion_amount.strip(),
        name=name.strip(),
        component_yield=component_yield.strip(),
        preparation_text=preparation_text.strip(),
        sort_order=sort_order,
    )
    session.add(component)
    session.commit()
    session.refresh(component)
    return component


def get_component(session: Session, component_id: int, dish_id: int) -> Optional[Component]:
    stmt = (
        select(Component)
        .options(selectinload(Component.ingredients))
        .where(Component.id == component_id, Component.dish_id == dish_id)
    )
    return session.scalar(stmt)


def update_component(session: Session, component: Component, data: dict[str, str]) -> Component:
    component.portion_amount = data["portion_amount"].strip()
    component.name = data["name"].strip()
    component.component_yield = data["component_yield"].strip()
    component.preparation_text = data["preparation_text"].strip()
    session.add(component)
    session.commit()
    session.refresh(component)
    return component


def delete_component(session: Session, component: Component) -> None:
    session.delete(component)
    session.commit()


def add_ingredient(session: Session, component: Component, name: str, amount: float) -> Ingredient:
    ingredient = Ingredient(
        component_id=component.id,
        name=name.strip(),
        amount=amount,
        sort_order=len(component.ingredients),
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


def delete_dish(session: Session, dish: Dish) -> None:
    session.delete(dish)
    session.commit()
