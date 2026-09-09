import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order
from app.schemas import OrderOut, QueryRequest, QueryResponse
from app.llm_service import answer_query

app = FastAPI(
    title="Cars24 AI Operations Copilot",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@app.get("/orders", response_model=list[OrderOut])
def list_orders(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Order).offset(skip).limit(limit).all()


@app.post("/query", response_model=QueryResponse)
def query_copilot(request: QueryRequest, db: Session = Depends(get_db)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    result = answer_query(db, request.query)
    return QueryResponse(**result)
