import datetime
from pathlib import Path
from sqlalchemy import String, Integer, Float, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import create_engine


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    price: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="在售")


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="已完成")
    channel: Mapped[str] = mapped_column(String(16))
    create_time: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)


class Traffic(Base):
    __tablename__ = "traffic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    channel: Mapped[str] = mapped_column(String(16))
    product_id: Mapped[str] = mapped_column(String(16), nullable=True, index=True)
    uv: Mapped[int] = mapped_column(Integer)
    pv: Mapped[int] = mapped_column(Integer)
    add_cart: Mapped[int] = mapped_column(Integer)


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), index=True)
    order_id: Mapped[str] = mapped_column(String(32))
    rating: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    create_time: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)


class Refund(Base):
    __tablename__ = "refunds"

    refund_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(256))
    create_time: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[datetime.date] = mapped_column(Date, index=True)
    anomaly_count: Mapped[int] = mapped_column(Integer)
    high_count: Mapped[int] = mapped_column(Integer)
    anomalies_json: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.now)


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
engine = create_engine(f"sqlite:///{(DATA_DIR / 'shop.db').as_posix()}")

def init_db():
    Base.metadata.create_all(engine)