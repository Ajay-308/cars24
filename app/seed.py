import random
from datetime import datetime, timedelta

from faker import Faker

from app.database import Base, engine, SessionLocal
from app.models import (
    Customer, Vehicle, Order, Payment, Delivery,
    OrderStatus, PaymentStatus, DeliveryStatus,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

VEHICLE_CATALOG = [
    ("Maruti Suzuki", "Swift", 2020), ("Maruti Suzuki", "Baleno", 2021),
    ("Hyundai", "Creta", 2022), ("Hyundai", "i20", 2019),
    ("Tata", "Nexon", 2021), ("Tata", "Punch", 2023),
    ("Honda", "City", 2020), ("Honda", "Amaze", 2019),
    ("Toyota", "Innova Crysta", 2021), ("Toyota", "Glanza", 2022),
    ("Kia", "Seltos", 2022), ("Mahindra", "XUV700", 2023),
    ("Volkswagen", "Polo", 2018), ("Renault", "Kwid", 2019),
    ("Skoda", "Rapid", 2020),
]

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery"]
DELIVERY_PARTNERS = ["Cars24 Logistics", "BlueDart", "Delhivery", "Local Hub Pickup"]


def build_seed_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        customers = []
        for _ in range(25):
            c = Customer(name=fake.name(), phone=fake.msisdn()[:10], email=fake.email())
            db.add(c)
            customers.append(c)
        db.flush()

        vehicles = []
        for make, model, year in VEHICLE_CATALOG:
            v = Vehicle(make=make, model=model, year=year,
                        price=round(random.uniform(350000, 1800000), 2))
            db.add(v)
            vehicles.append(v)
        db.flush()

        for i in range(1, 61):
            customer = random.choice(customers)
            vehicle = random.choice(vehicles)
            created = datetime.utcnow() - timedelta(days=random.randint(1, 45))

            order_status = random.choices(
                [OrderStatus.PLACED, OrderStatus.CONFIRMED,
                 OrderStatus.COMPLETED, OrderStatus.CANCELLED],
                weights=[0.15, 0.35, 0.40, 0.10],
            )[0]

            order = Order(
                id=i, customer_id=customer.id, vehicle_id=vehicle.id,
                amount=vehicle.price, status=order_status, created_at=created,
            )
            db.add(order)

            # Payment status correlates loosely with order status, but we
            # deliberately inject mismatches (paid + not_scheduled delivery,
            # confirmed order + failed payment) so the copilot has real
            # "what's going on" scenarios to reason about.
            if order_status == OrderStatus.CANCELLED:
                pay_status = random.choice([PaymentStatus.REFUNDED, PaymentStatus.FAILED])
            elif order_status == OrderStatus.PLACED:
                pay_status = random.choice([PaymentStatus.PENDING, PaymentStatus.PAID])
            else:
                pay_status = random.choices(
                    [PaymentStatus.PAID, PaymentStatus.PENDING, PaymentStatus.FAILED],
                    weights=[0.85, 0.10, 0.05],
                )[0]

            paid_at = created + timedelta(hours=random.randint(1, 48)) \
                if pay_status == PaymentStatus.PAID else None

            payment = Payment(
                order_id=i, amount=vehicle.price, status=pay_status,
                method=random.choice(PAYMENT_METHODS), paid_at=paid_at,
            )
            db.add(payment)

            # Delivery logic: if unpaid, delivery is never scheduled.
            # If paid, most are scheduled/delivered, but ~12% are stuck
            # "not_scheduled" despite payment -- the classic support
            # escalation the copilot should be able to flag.
            if pay_status != PaymentStatus.PAID:
                del_status = DeliveryStatus.NOT_SCHEDULED
                scheduled = delivered = None
            else:
                del_status = random.choices(
                    [DeliveryStatus.DELIVERED, DeliveryStatus.IN_TRANSIT,
                     DeliveryStatus.SCHEDULED, DeliveryStatus.DELAYED,
                     DeliveryStatus.NOT_SCHEDULED],
                    weights=[0.45, 0.15, 0.20, 0.08, 0.12],
                )[0]
                scheduled = paid_at + timedelta(days=random.randint(1, 5)) \
                    if del_status != DeliveryStatus.NOT_SCHEDULED else None
                delivered = scheduled + timedelta(days=random.randint(0, 2)) \
                    if del_status == DeliveryStatus.DELIVERED else None

            notes = None
            if del_status == DeliveryStatus.DELAYED:
                notes = random.choice([
                    "Vehicle inspection re-check required.",
                    "Logistics partner reported a delay due to weather.",
                    "Customer requested a rescheduled delivery slot.",
                ])
            elif del_status == DeliveryStatus.NOT_SCHEDULED and pay_status == PaymentStatus.PAID:
                notes = "Payment confirmed but delivery slot not yet allocated -- needs ops follow-up."

            delivery = Delivery(
                order_id=i, status=del_status, scheduled_date=scheduled,
                delivered_date=delivered,
                partner=random.choice(DELIVERY_PARTNERS) if del_status != DeliveryStatus.NOT_SCHEDULED else None,
                notes=notes,
            )
            db.add(delivery)

        db.commit()
        print("Seed data created: 25 customers, 15 vehicles, 60 orders (with payments & deliveries).")
    finally:
        db.close()


if __name__ == "__main__":
    build_seed_data()
