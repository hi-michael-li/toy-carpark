from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel


class Organization(BaseModel):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    billing_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("organization_plans.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    members: Mapped[list["OrganizationMember"]] = relationship(back_populates="org")
    plans: Mapped[list["OrganizationPlan"]] = relationship(
        back_populates="org",
        foreign_keys="OrganizationPlan.organization_id",
    )
    billing_plan: Mapped["OrganizationPlan | None"] = relationship(
        foreign_keys=[billing_plan_id],
    )


class OrganizationPlan(BaseModel):
    __tablename__ = "organization_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_stations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    org: Mapped["Organization | None"] = relationship(
        back_populates="plans",
        foreign_keys=[organization_id],
    )


class OrganizationMember(BaseModel):
    __tablename__ = "organization_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    org: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="org_memberships")  # noqa: F821
