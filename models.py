from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    final_yield: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    photo_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    processed_photo_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    voice_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    components: Mapped[list["Component"]] = relationship(
        back_populates="dish", cascade="all, delete-orphan", order_by="Component.sort_order"
    )


class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    portion_amount: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_yield: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    preparation_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    dish: Mapped[Dish] = relationship(back_populates="components")
    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="component", cascade="all, delete-orphan", order_by="Ingredient.sort_order"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("components.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    component: Mapped[Component] = relationship(back_populates="ingredients")
