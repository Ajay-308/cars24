from sqlalchemy.orm import Session

from app.models import Order, Customer


def get_order_summary(db: Session, order_id: int) -> dict:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"error": f"No order found with id {order_id}"}

    return {
        "order_id": order.id,
        "order_status": order.status.value,
        "amount": order.amount,
        "created_at": order.created_at.isoformat(),
        "customer": {"name": order.customer.name, "phone": order.customer.phone},
        "vehicle": f"{order.vehicle.year} {order.vehicle.make} {order.vehicle.model}",
        "payment": {
            "status": order.payment.status.value if order.payment else "no_payment_record",
            "amount": order.payment.amount if order.payment else None,
            "method": order.payment.method if order.payment else None,
            "paid_at": order.payment.paid_at.isoformat() if order.payment and order.payment.paid_at else None,
        },
        "delivery": {
            "status": order.delivery.status.value if order.delivery else "no_delivery_record",
            "scheduled_date": order.delivery.scheduled_date.isoformat() if order.delivery and order.delivery.scheduled_date else None,
            "delivered_date": order.delivery.delivered_date.isoformat() if order.delivery and order.delivery.delivered_date else None,
            "partner": order.delivery.partner if order.delivery else None,
            "notes": order.delivery.notes if order.delivery else None,
        },
    }


def get_payment_status(db: Session, order_id: int) -> dict:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"error": f"No order found with id {order_id}"}
    if not order.payment:
        return {"order_id": order_id, "payment_status": "no_payment_record"}
    return {
        "order_id": order_id,
        "payment_status": order.payment.status.value,
        "amount": order.payment.amount,
        "method": order.payment.method,
        "paid_at": order.payment.paid_at.isoformat() if order.payment.paid_at else None,
    }


def get_delivery_status(db: Session, order_id: int) -> dict:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"error": f"No order found with id {order_id}"}
    if not order.delivery:
        return {"order_id": order_id, "delivery_status": "no_delivery_record"}
    return {
        "order_id": order_id,
        "delivery_status": order.delivery.status.value,
        "scheduled_date": order.delivery.scheduled_date.isoformat() if order.delivery.scheduled_date else None,
        "delivered_date": order.delivery.delivered_date.isoformat() if order.delivery.delivered_date else None,
        "partner": order.delivery.partner,
        "notes": order.delivery.notes,
    }


def search_orders_by_customer(db: Session, name_or_phone: str) -> dict:
    customers = db.query(Customer).filter(
        (Customer.name.ilike(f"%{name_or_phone}%")) |
        (Customer.phone.ilike(f"%{name_or_phone}%"))
    ).all()
    if not customers:
        return {"error": f"No customer found matching '{name_or_phone}'"}

    results = []
    for c in customers:
        for order in c.orders:
            results.append({
                "order_id": order.id,
                "customer_name": c.name,
                "order_status": order.status.value,
                "payment_status": order.payment.status.value if order.payment else None,
                "delivery_status": order.delivery.status.value if order.delivery else None,
            })
    return {"matches": results}


def list_orders_needing_attention(db: Session) -> dict:
    orders = db.query(Order).all()
    flagged = []
    for order in orders:
        if (order.payment and order.payment.status.value == "paid" and
                order.delivery and order.delivery.status.value == "not_scheduled"):
            flagged.append({
                "order_id": order.id,
                "customer_name": order.customer.name,
                "paid_at": order.payment.paid_at.isoformat() if order.payment.paid_at else None,
            })
    return {"flagged_orders": flagged, "count": len(flagged)}



