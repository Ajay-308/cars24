from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CustomerOut(BaseModel):
    id: int
    name: str
    phone: str
    email: str

    class Config:
        from_attributes = True


class VehicleOut(BaseModel):
    id: int
    make: str
    model: str
    year: int
    price: float

    class Config:
        from_attributes = True


class PaymentOut(BaseModel):
    id: int
    status: str
    amount: float
    method: str
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeliveryOut(BaseModel):
    id: int
    status: str
    scheduled_date: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    partner: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    status: str
    amount: float
    created_at: datetime
    customer: CustomerOut
    vehicle: VehicleOut
    payment: Optional[PaymentOut] = None
    delivery: Optional[DeliveryOut] = None

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    mode: str 
    data: Optional[dict] = None 
