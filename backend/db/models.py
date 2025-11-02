from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Fighter(Base):
    __tablename__ = "fighters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    nickname: Mapped[str | None]
    division: Mapped[str | None]
    height: Mapped[str | None]
    weight: Mapped[str | None]
    reach: Mapped[str | None]
    leg_reach: Mapped[str | None]
    stance: Mapped[str | None]
    dob: Mapped[date | None]
    record: Mapped[str | None]
    sherdog_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    image_scraped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    fights: Mapped[list["Fight"]] = relationship("Fight", back_populates="fighter")


class Fight(Base):
    __tablename__ = "fights"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    fighter_id: Mapped[str] = mapped_column(ForeignKey("fighters.id"), nullable=False)
    opponent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    opponent_name: Mapped[str] = mapped_column(String, nullable=False)
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    event_date: Mapped[date | None]
    result: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str | None]
    round: Mapped[int | None]
    time: Mapped[str | None]
    fight_card_url: Mapped[str | None]

    fighter: Mapped[Fighter] = relationship("Fighter", back_populates="fights")


fighter_stats = Table(
    "fighter_stats",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fighter_id", ForeignKey("fighters.id"), nullable=False),
    Column("category", String, nullable=False),
    Column("metric", String, nullable=False),
    Column("value", String, nullable=False),
)
