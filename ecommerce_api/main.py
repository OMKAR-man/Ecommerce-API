import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel

#load env
load_dotenv(r"C:\Users\DELL LAPTOP\Desktop\ecommerce_api\cred.env")

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

import mysql.connector
from mysql.connector import Error
import jwt
from passlib.context import CryptContext

#app
app = FastAPI(title="Simple Shop API")
 
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

print("DB_HOST =", os.getenv("DB_HOST"))
print("DB_USER =", os.getenv("DB_USER"))
print("DB_PASSWORD =", os.getenv("DB_PASSWORD"))
print("DB_NAME =", os.getenv("DB_NAME"))


secret_key = secrets.token_urlsafe(20)
print("SECRET_KEY =", secret_key)

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_EXPIRE_MIN = int(os.getenv("TOKEN_EXPIRE_MIN", 60))

security = HTTPBearer()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

#models
class RegisterModel(BaseModel):
    email: EmailStr
    password: str

class LoginModel(BaseModel):
    email: EmailStr
    password: str


class ProductModel(BaseModel):
    name: str
    price: float
    stock: int


class ProductUpdateModel(BaseModel):
    name: str
    price: float
    stock: int


class ProductPatchModel(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None    


#db

def get_conn():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise HTTPException(500, f"MySQL error: {e}")


#pass

def hash_password(pw: str):
    return pwd.hash(pw)

def verify_password(pw, hashed):
    return pwd.verify(pw, hashed)


#jwt

def create_token(user_id: int):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MIN)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


#root

@app.get("/")
def root():
    return {"msg": "Simple Shop API Running"}


#register

@app.post("/register")
def register(data: RegisterModel):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s,%s)",
            (data.email, hash_password(data.password))
        )
        conn.commit()
        return {"user_id": cur.lastrowid}

    except mysql.connector.IntegrityError:
        raise HTTPException(400, "Email exists")

    finally:
        cur.close()
        conn.close()


#login

@app.post("/login")
def login(data: LoginModel):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    # check email
    cur.execute("SELECT * FROM users WHERE email=%s", (data.email,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        raise HTTPException(404, "User not registered. Please register first.")

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Wrong login credentials")

    token = create_token(user["user_id"])

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer"
    }

#create prod

@app.post("/products")
def create_product(p: ProductModel, payload=Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO products (name, price, stock) VALUES (%s,%s,%s)",
        (p.name, p.price, p.stock)
    )
    conn.commit()

    pid = cur.lastrowid

    cur.close()
    conn.close()

    return {"message": "Product created", "product_id": pid}


#get

@app.get("/products")
def get_products():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


#get one

@app.get("/products/{pid}")
def get_product(pid: int):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products WHERE product_id=%s", (pid,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        raise HTTPException(404, "Product not found")

    return row


#update

@app.put("/products/{pid}")
def update_product(pid: int, p: ProductUpdateModel, payload=Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "UPDATE products SET name=%s, price=%s, stock=%s WHERE product_id=%s",
        (p.name, p.price, p.stock, pid)
    )
    conn.commit()

    if cur.rowcount == 0:
        raise HTTPException(404, "Product not found")

    cur.close()
    conn.close()

    return {"message": "Product updated"}


#patch

@app.patch("/products/{pid}")
def patch_product(pid: int, p: ProductPatchModel, payload=Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products WHERE product_id=%s", (pid,))
    existing = cur.fetchone()

    if not existing:
        raise HTTPException(404, "Product not found")

    name = p.name or existing["name"]
    price = p.price or existing["price"]
    stock = p.stock or existing["stock"]

    cur.execute(
        "UPDATE products SET name=%s, price=%s, stock=%s WHERE product_id=%s",
        (name, price, stock, pid)
    )
    conn.commit()

    cur.close()
    conn.close()

    return {"message": "Product patched"}


#del

@app.delete("/products/{pid}")
def delete_product(pid: int, payload=Depends(verify_token)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE product_id=%s", (pid,))
    conn.commit()

    if cur.rowcount == 0:
        raise HTTPException(404, "Product not found")

    cur.close()
    conn.close()

    return {"message": "Product deleted"}


#list

@app.get("/products")
def get_products():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows
