from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # Datas sempre com fuso (modelo de dados, seção 1); texto é `text`, sem limite artificial.
    type_annotation_map = {datetime: DateTime(timezone=True), str: Text()}


def chave_primaria() -> Mapped[int]:
    """`bigint generated always as identity`: o banco gera, a aplicação nunca escolhe."""
    return mapped_column(BigInteger, Identity(always=True), primary_key=True)
