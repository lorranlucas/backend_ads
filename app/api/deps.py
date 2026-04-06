from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Header
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.tenant import Tenant
from app.core.security import ALGORITHM, SECRET_KEY
import uuid

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Header(None)
) -> User:
    if not token or token == "undefined" or token == "":
        # For development/demo purposes, we'll return a mock user if no token
        result = await db.execute(select(User))
        user = result.scalars().first()
        if user: 
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user

async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Tenant:
    # Need to ensure tenant is loaded or fetched
    result = await db.execute(select(Tenant).filter(Tenant.id == current_user.tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
