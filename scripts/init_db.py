#!/usr/bin/env python3
"""
Database Initialization Script for AI Agent Communication System.

This script initializes the PostgreSQL database with all required tables
and default data for the application to run.

Usage:
    python scripts/init_db.py              # Initialize database
    python scripts/init_db.py --reset       # Drop and recreate all tables
    python scripts/init_db.py --check       # Check database connection and status
    python scripts/init_db.py --seed        # Seed default data only

Environment Variables:
    DATABASE_URL: PostgreSQL connection URL
                    (default: postgresql+asyncpg://agent:password@localhost:5432/agent_comm)

Examples:
    # Initialize database with default settings
    python scripts/init_db.py

    # Reset database (WARNING: This will delete all data!)
    python scripts/init_db.py --reset

    # Check database connection and status
    python scripts/init_db.py --check
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Load .env file before importing project modules
from dotenv import load_dotenv
from sqlalchemy import text

# Try to load .env file from multiple locations
env_paths = [
    Path(__file__).parent.parent / ".env",  # Project root
    Path(__file__).parent.parent / ".env.production",  # Production config
    Path.cwd() / ".env",  # Current directory
    Path.cwd() / ".env.production",  # Production in current dir
]
load_dotenv(dotenv_path=env_paths[0], override=True)  # Load .env if exists

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_comm_core.db.database import (
    close_db,
    get_engine,
    init_db,
)


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_step(step: int, total: int, text: str) -> None:
    """Print a step indicator."""
    print(f"{Colors.CYAN}[{step}/{total}] {Colors.BOLD}{text}{Colors.END}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"  {Colors.GREEN}✓{Colors.END} {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"  {Colors.RED}✗{Colors.END} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠{Colors.END} {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"  {Colors.BLUE}ℹ{Colors.END} {text}")


async def check_database_status(database_url: str | None = None) -> bool:
    """
    Check database connection and current status.

    Args:
        database_url: Database connection URL

    Returns:
        True if database is accessible, False otherwise
    """
    print_step(1, 1, "Checking database connection")

    try:
        engine = get_engine(database_url)

        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute("SELECT version()")
            version = result.scalar()
            print_success("Connected to PostgreSQL")
            print_info(f"Version: {version}")

        # Check if tables exist
        async with engine.connect() as conn:
            result = await conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row[0] for row in result.fetchall()]

            if tables:
                print_success(f"Found {len(tables)} tables:")
                for table in tables:
                    print_info(f"  - {table}")
            else:
                print_warning("No tables found. Database needs initialization.")

        return True

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False
    finally:
        await close_db()


async def create_database(
    db_name: str = "agent_comm",
    admin_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/postgres",
) -> bool:
    """
    Create PostgreSQL database if it doesn't exist.

    Args:
        db_name: Database name to create
        admin_url: Connection URL to postgres database (admin access)

    Returns:
        True if database exists or was created, False otherwise
    """
    print_step(1, 3, "Creating database (if needed)")

    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        # Connect to postgres database to create new database
        engine = create_async_engine(admin_url, echo=False)

        try:
            # Check if database exists
            async with engine.connect() as conn:
                result = await conn.execute(
                    f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
                )
                exists = result.fetchone() is not None

                if exists:
                    print_success(f"Database '{db_name}' already exists")
                    return True

            # Create database
            async with engine.connect() as conn:
                # Disconnect from current connection before creating database
                await conn.commit()

            # Use autocommit for CREATE DATABASE
            engine2 = create_async_engine(admin_url, isolation_level="AUTOCOMMIT", echo=False)
            try:
                async with engine2.connect() as conn:
                    await conn.execute(f'CREATE DATABASE "{db_name}"')
                    print_success(f"Created database '{db_name}'")
                return True
            finally:
                await engine2.dispose()

        finally:
            await engine.dispose()

    except Exception as e:
        print_error(f"Failed to create database: {e}")
        print_info("Tip: Make sure PostgreSQL is running and admin credentials are correct")
        print_info("You can also create the database manually:")
        print_info(f"  createdb {db_name}")
        return False


async def initialize_tables(
    database_url: str | None = None,
    drop_all: bool = False,
) -> bool:
    """
    Initialize database tables.

    Args:
        database_url: Database connection URL
        drop_all: Drop all existing tables before creating

    Returns:
        True if successful, False otherwise
    """
    step_num = 2
    total_steps = 4

    print_step(step_num, total_steps, "Initializing database tables")
    step_num += 1

    try:
        if drop_all:
            print_warning("Drop all mode enabled - all existing data will be lost!")
            response = input("  Type 'yes' to confirm: ")
            if response.lower() != "yes":
                print_info("Operation cancelled")
                return False

        await init_db(database_url=database_url, drop_all=drop_all)
        print_success("Database tables initialized")

        return True

    except Exception as e:
        print_error(f"Failed to initialize tables: {e}")
        return False


async def seed_default_data(database_url: str | None = None) -> bool:
    """
    Seed default data into the database.

    Creates:
    - Default project (proj_main)
    - Admin user (if not exists)

    Args:
        database_url: Database connection URL

    Returns:
        True if successful, False otherwise
    """
    step_num = 3
    total_steps = 4

    print_step(step_num, total_steps, "Seeding default data")
    step_num += 1

    try:
        from passlib.context import CryptContext

        from agent_comm_core.db.database import db_session
        from agent_comm_core.db.models.project import ProjectDB
        from agent_comm_core.db.models.user import UserDB
        from mcp_broker.project.registry import get_project_registry

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async with db_session(database_url) as session:
            # Check if default project exists
            result = await session.execute(
                text("SELECT project_id FROM projects WHERE project_id = 'proj_main'")
            )
            default_project_exists = result.fetchone() is not None

            # Get or create admin user first (projects require owner)
            result = await session.execute(text("SELECT id FROM users WHERE username = 'admin'"))
            admin_row = result.fetchone()

            if not admin_row:
                # Create admin user first
                admin_password = pwd_context.hash("admin")  # Default password, should be changed
                admin_user = UserDB(
                    username="admin",
                    email="admin@example.com",
                    hashed_password=admin_password,
                    is_active=True,
                    is_superuser=True,
                )
                session.add(admin_user)
                await session.flush()  # Get the user ID
                admin_id = admin_user.id
                print_success("Created admin user (username: admin, password: admin)")
                print_warning("IMPORTANT: Change the default admin password immediately!")
            else:
                admin_id = admin_row[0]
                print_success("Admin user already exists")

            # Now create default project if needed
            if not default_project_exists:
                # Create default project
                # Note: project_id is the human-readable ID, id is auto-generated UUID
                default_project = ProjectDB(
                    project_id="proj_main",
                    name="Main Project",
                    description="Default project for general use",
                    status="active",
                    owner_id=admin_id,  # Link to admin user
                )
                session.add(default_project)
                print_success("Created default project 'proj_main'")
            else:
                print_success("Default project 'proj_main' already exists")

        # Initialize MCP Broker default project
        registry = get_project_registry()
        if not await registry.get_project("default"):
            await registry.create_project(
                project_id="default",
                name="Default Project",
                description="Default project for MCP Broker",
            )
            print_success("Created MCP Broker default project")
        else:
            print_success("MCP Broker default project already exists")

        return True

    except Exception as e:
        print_error(f"Failed to seed default data: {e}")
        return False


async def verify_initialization(database_url: str | None = None) -> bool:
    """
    Verify that the database was initialized correctly.

    Args:
        database_url: Database connection URL

    Returns:
        True if verification passed, False otherwise
    """
    step_num = 4
    total_steps = 4

    print_step(step_num, total_steps, "Verifying initialization")
    step_num += 1

    try:
        from agent_comm_core.db.database import db_session

        async with db_session(database_url) as session:
            # Check tables
            result = await session.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            expected_tables = {
                "users",
                "projects",
                "agent_api_keys",
                "chat_rooms",
                "messages",
                "meetings",
                "meeting_participants",
                "meeting_messages",
                "decisions",
                "agent_comm_communications",
                "agent_comm_meetings",
                "agent_comm_meeting_participants",
                "agent_comm_meeting_messages",
                "agent_comm_decisions",
                "audit_logs",
            }

            missing_tables = expected_tables - set(tables)

            if missing_tables:
                print_error(f"Missing tables: {missing_tables}")
                return False

            print_success(f"All {len(expected_tables)} tables verified")

            # Check default project
            result = await session.execute(
                "SELECT id, name, status FROM projects WHERE id = 'proj_main'"
            )
            project = result.fetchone()

            if project:
                print_success(f"Default project found: {project[1]} (status: {project[2]})")
            else:
                print_warning("Default project 'proj_main' not found")

            # Check admin user
            result = await session.execute(
                "SELECT username, is_superuser FROM users WHERE username = 'admin'"
            )
            admin = result.fetchone()

            if admin:
                print_success(f"Admin user found: {admin[0]} (superuser: {admin[1]})")
            else:
                print_warning("Admin user not found")

        return True

    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False


async def main() -> int:
    """
    Main entry point for database initialization.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Initialize database for AI Agent Communication System"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all existing tables and recreate (WARNING: This will delete all data!)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check database connection and status only",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed default data only (skip table creation)",
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Create PostgreSQL database if it doesn't exist",
    )
    parser.add_argument(
        "--admin-url",
        default="postgresql+asyncpg://postgres:password@localhost:5432/postgres",
        help="Admin connection URL for database creation (default: postgresql+asyncpg://postgres:password@localhost:5432/postgres)",
    )
    parser.add_argument(
        "--db-name",
        default="agent_comm",
        help="Database name to create (default: agent_comm)",
    )

    args = parser.parse_args()

    # Get database URL from environment
    from os import getenv

    database_url = getenv("DATABASE_URL")

    print_header("AI Agent Communication System - Database Initialization")

    if args.check:
        # Check mode only
        success = await check_database_status(database_url)
        return 0 if success else 1

    if args.seed:
        # Seed mode only
        success = await seed_default_data(database_url)
        return 0 if success else 1

    # Full initialization
    success = True

    # Step 1: Create database (if requested)
    if args.create_db:
        if not await create_database(args.db_name, args.admin_url):
            return 1

    # Step 2-4: Initialize tables, seed data, verify
    if not await initialize_tables(database_url, args.reset):
        return 1

    if not await seed_default_data(database_url):
        return 1

    if not await verify_initialization(database_url):
        return 1

    # Summary
    print_header("Initialization Complete")

    print_success("Database is ready for use!")
    print()
    print_info("Default credentials:")
    print_info("  Admin username: admin")
    print_info("  Admin password: admin (CHANGE THIS IMMEDIATELY!)")
    print()
    print_info("Next steps:")
    print_info("  1. Start the communication server:")
    print_info("     python src/communication_server/main.py")
    print()
    print_info("  2. Or start with Docker Compose:")
    print_info("     docker-compose up -d")
    print()
    print_info("  3. Access the dashboard at:")
    print_info("     http://localhost:8000")

    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
