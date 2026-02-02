"""
Authentication API endpoints.

Provides login, logout, token refresh, and user management for dashboard users,
as well as agent token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from agent_comm_core.models.auth import (
    AgentTokenCreate,
    AgentTokenResponse,
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    Token,
    User,
    UserCreate,
    UserRole,
)
from communication_server.security.auth import AuthService, get_auth_service
from communication_server.security.dependencies import get_current_admin, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AgentTokenRequest(BaseModel):
    """Simple request model for creating agent token (nickname only)."""

    nickname: str = Field(..., description="Agent display name", min_length=1, max_length=100)


@router.post("/token", response_model=dict)
async def create_token(
    request: AgentTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Create a new API token for an agent (public endpoint).

    This endpoint allows anyone to create an agent token by providing
    a nickname. No authentication required.

    Args:
        token_data: Agent token creation data (nickname required)
        auth_service: Authentication service

    Returns:
        Created agent token with agent information
    """
    # Create agent token with default project_id
    token, agent = await auth_service.create_agent_token(
        project_id="default",
        nickname=request.nickname,
        capabilities=["mcp"],
    )

    return {
        "token": token,
        "agent_id": agent.id,
        "nickname": agent.nickname,
        "message": "Store this token securely. It will not be shown again.",
    }


@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a dashboard user and return JWT tokens.

    Args:
        credentials: Username and password
        auth_service: Authentication service

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If authentication fails
    """
    # Validate password length
    if len(credentials.password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters long",
        )

    # Authenticate user
    user = await auth_service.authenticate_dashboard_user(
        credentials.username, credentials.password
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    tokens = await auth_service.create_user_tokens(user.id)

    return Token(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh an access token using a refresh token.

    Args:
        request: Refresh token
        auth_service: Authentication service

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    access_token = await auth_service.refresh_access_token(request.refresh_token)

    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Create new refresh token
    from communication_server.security.tokens import verify_jwt_token

    try:
        token_data = verify_jwt_token(request.refresh_token)
        new_refresh_token = await auth_service.create_user_tokens(token_data.user_id)

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token["refresh_token"],
            token_type="bearer",
            expires_in=15 * 60,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from err


@router.post("/logout")
async def logout(
    refresh_token: RefreshTokenRequest,
    _current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Logout a user by revoking their tokens.

    Args:
        refresh_token: Refresh token to revoke
        _current_user: Currently authenticated user (authentication only)
        auth_service: Authentication service

    Returns:
        Success message
    """
    # Revoke the refresh token (user authentication is enforced by dependency)
    await auth_service.revoke_token(refresh_token.refresh_token, "refresh")

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Args:
        current_user: Currently authenticated user

    Returns:
        User information
    """
    return current_user


@router.post("/signup", response_model=User)
async def signup(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Create a new user account (public endpoint).

    Allows anyone to create a new user account with username and password.
    The password must be at least 12 characters long.

    Args:
        user_data: User creation data
        auth_service: Authentication service

    Returns:
        Created user

    Raises:
        HTTPException: If user already exists or validation fails
    """
    from agent_comm_core.db.database import db_session
    from agent_comm_core.repositories import UserRepository

    # Force role to USER for public signup (security measure)
    if user_data.role != UserRole.USER:
        user_data.role = UserRole.USER

    # Generate default email from username if not provided
    email = getattr(user_data, "email", None) or f"{user_data.username}@localhost"

    async with db_session() as session:
        repo = UserRepository(session)

        # Check if user already exists
        if await repo.username_exists(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )

        # Check if email already exists
        if await repo.email_exists(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        # Create user in database
        password_hash = auth_service._hash_password(user_data.password)
        user_db = await repo.create(
            username=user_data.username,
            email=email,
            password_hash=password_hash,
            role=user_data.role.value,
            permissions=user_data.permissions,
        )
        await session.commit()

        return User(
            id=str(user_db.id),
            username=user_db.username,
            role=user_data.role,
            permissions=user_data.permissions,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
        )


@router.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    _current_admin: User = Depends(get_current_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Create a new user (admin only).

    Args:
        user_data: User creation data
        _current_admin: Currently authenticated admin (authentication only)
        auth_service: Authentication service

    Returns:
        Created user

    Raises:
        HTTPException: If user already exists or lacks admin privileges
    """
    from agent_comm_core.db.database import db_session
    from agent_comm_core.repositories import UserRepository

    # Generate default email from username if not provided
    email = getattr(user_data, "email", None) or f"{user_data.username}@localhost"

    async with db_session() as session:
        repo = UserRepository(session)

        # Check if user already exists
        if await repo.username_exists(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists",
            )

        # Check if email already exists
        if await repo.email_exists(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        # Create user in database
        password_hash = auth_service._hash_password(user_data.password)
        user_db = await repo.create(
            username=user_data.username,
            email=email,
            password_hash=password_hash,
            role=user_data.role.value,
            permissions=user_data.permissions,
        )
        await session.commit()

        return User(
            id=str(user_db.id),
            username=user_db.username,
            role=user_data.role,
            permissions=user_data.permissions,
            is_active=user_db.is_active,
            created_at=user_db.created_at,
        )


@router.post("/agent-tokens", response_model=AgentTokenResponse)
async def create_agent_token(
    token_data: AgentTokenCreate,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Create a new API token for an agent (requires user authentication).

    Args:
        token_data: Agent token creation data
        current_user: Currently authenticated user
        auth_service: Authentication service

    Returns:
        Created agent token

    Raises:
        HTTPException: If user lacks write permissions
    """
    if not current_user.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permissions required",
        )

    # Create agent token
    token, agent = await auth_service.create_agent_token(
        project_id=token_data.project_id,
        nickname=token_data.nickname,
        capabilities=token_data.capabilities,
    )

    return AgentTokenResponse(
        token=token,
        agent_id=agent.id,
        message="Store this token securely. It will not be shown again.",
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Change the current user's password.

    Args:
        password_data: Current and new password
        current_user: Currently authenticated user
        auth_service: Authentication service

    Returns:
        Success message

    Raises:
        HTTPException: If current password is incorrect
    """
    from uuid import UUID

    from agent_comm_core.db.database import db_session
    from agent_comm_core.repositories import UserRepository

    async with db_session() as session:
        repo = UserRepository(session)

        # Get user from database
        user_db = await repo.get_by_id(UUID(current_user.id))
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Verify current password
        if not auth_service._verify_password(password_data.current_password, user_db.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        # Update password
        new_password_hash = auth_service._hash_password(password_data.new_password)
        await repo.update_password(user_db.id, new_password_hash)
        await session.commit()

        return {"message": "Password changed successfully"}
