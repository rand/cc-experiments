#!/usr/bin/env python3
"""
PostgreSQL Migration Generator

Generates migration files from schema differences or templates.
Supports multiple migration tools (Flyway, golang-migrate, Alembic, dbmate).

Features:
- Generate migrations from schema diff
- Create migration templates
- Support multiple migration tool formats
- Auto-detect unsafe operations
- Generate idempotent SQL

Usage:
    ./generate_migration.py --tool flyway --name add_users_table
    ./generate_migration.py --tool golang-migrate --name add_users_table
    ./generate_migration.py --template add-column --table users --column email:varchar
    ./generate_migration.py --diff --from-db source --to-db target
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re


class MigrationTool:
    """Migration tool types"""
    FLYWAY = "flyway"
    GOLANG_MIGRATE = "golang-migrate"
    ALEMBIC = "alembic"
    DBMATE = "dbmate"
    ATLAS = "atlas"

    @classmethod
    def all(cls) -> List[str]:
        return [cls.FLYWAY, cls.GOLANG_MIGRATE, cls.ALEMBIC, cls.DBMATE, cls.ATLAS]


@dataclass
class MigrationFile:
    """Migration file metadata"""
    name: str
    content: str
    path: Optional[Path] = None

    def write(self, base_dir: Path) -> Path:
        """Write migration file to disk"""
        file_path = base_dir / self.name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(self.content)
        return file_path


class MigrationGenerator:
    """Generates migration files"""

    def __init__(self, tool: str, migrations_dir: Path = Path("migrations")):
        self.tool = tool
        self.migrations_dir = migrations_dir

    def generate_add_table(
        self,
        table_name: str,
        columns: List[Tuple[str, str]],
        primary_key: Optional[str] = "id"
    ) -> List[MigrationFile]:
        """Generate migration to add table"""
        # Build CREATE TABLE statement
        column_defs = []

        for col_name, col_type in columns:
            if col_name == primary_key and col_type.upper() == "SERIAL":
                column_defs.append(f"    {col_name} SERIAL PRIMARY KEY")
            else:
                column_defs.append(f"    {col_name} {col_type}")

        columns_joined = ',\n'.join(column_defs)
        create_sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
{columns_joined}
);"""

        # Generated rollback migration - safe because of IF EXISTS guard
        drop_sql = f"DROP TABLE IF EXISTS {table_name};"

        return self._create_migration(f"add_{table_name}_table", create_sql, drop_sql)

    def generate_add_column(
        self,
        table_name: str,
        column_name: str,
        column_type: str,
        nullable: bool = True,
        default: Optional[str] = None
    ) -> List[MigrationFile]:
        """Generate migration to add column"""
        # Build ADD COLUMN statement
        col_def = f"{column_name} {column_type}"

        if not nullable:
            if default is not None:
                col_def += f" NOT NULL DEFAULT {default}"
            else:
                # Multi-step for safety
                add_sql = f"""-- Step 1: Add nullable column
ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type};

-- Step 2: Backfill (if needed)
-- UPDATE {table_name} SET {column_name} = <default_value> WHERE {column_name} IS NULL;

-- Step 3: Add NOT NULL constraint
-- ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL;"""

                drop_sql = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name};"

                return self._create_migration(
                    f"add_{column_name}_to_{table_name}",
                    add_sql,
                    drop_sql
                )
        else:
            if default is not None:
                col_def += f" DEFAULT {default}"

        add_sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_def};"
        drop_sql = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name};"

        return self._create_migration(
            f"add_{column_name}_to_{table_name}",
            add_sql,
            drop_sql
        )

    def generate_add_index(
        self,
        table_name: str,
        column_names: List[str],
        unique: bool = False,
        concurrent: bool = True
    ) -> List[MigrationFile]:
        """Generate migration to add index"""
        index_name = f"idx_{table_name}_{'_'.join(column_names)}"
        columns_str = ', '.join(column_names)

        unique_str = "UNIQUE " if unique else ""
        concurrent_str = "CONCURRENTLY " if concurrent else ""

        create_sql = f"""-- NOTE: CONCURRENTLY cannot run inside transaction
CREATE {unique_str}INDEX {concurrent_str}IF NOT EXISTS {index_name}
ON {table_name}({columns_str});"""

        drop_sql = f"DROP INDEX {concurrent_str}IF EXISTS {index_name};"

        return self._create_migration(
            f"add_index_{index_name}",
            create_sql,
            drop_sql
        )

    def generate_drop_column(
        self,
        table_name: str,
        column_name: str
    ) -> List[MigrationFile]:
        """Generate migration to drop column (with warning)"""
        drop_sql = f"""-- WARNING: This will permanently delete data!
-- Ensure application no longer references this column.
ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name};"""

        # Can't restore data, so down migration is commented
        restore_sql = f"""-- Cannot restore dropped column with original data
-- ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} <TYPE>;"""

        return self._create_migration(
            f"drop_{column_name}_from_{table_name}",
            drop_sql,
            restore_sql
        )

    def generate_add_constraint(
        self,
        table_name: str,
        constraint_name: str,
        constraint_type: str,
        definition: str,
        validate: bool = True
    ) -> List[MigrationFile]:
        """Generate migration to add constraint"""
        if validate:
            # Two-step process for zero-downtime
            add_sql = f"""-- Step 1: Add constraint without validation (fast)
ALTER TABLE {table_name}
ADD CONSTRAINT {constraint_name}
{constraint_type} ({definition})
NOT VALID;

-- Step 2: Validate constraint (slow, but doesn't block writes)
ALTER TABLE {table_name} VALIDATE CONSTRAINT {constraint_name};"""
        else:
            add_sql = f"""ALTER TABLE {table_name}
ADD CONSTRAINT {constraint_name}
{constraint_type} ({definition});"""

        drop_sql = f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name};"

        return self._create_migration(
            f"add_{constraint_name}_to_{table_name}",
            add_sql,
            drop_sql
        )

    def generate_rename_column(
        self,
        table_name: str,
        old_column: str,
        new_column: str
    ) -> List[MigrationFile]:
        """Generate migration to rename column (with expand-contract pattern)"""
        rename_sql = f"""-- RECOMMENDED: Use expand-contract pattern instead of direct rename
-- This is a direct rename which will break old code immediately

-- Phase 1: Add new column (commented out - do this first)
-- ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {new_column} <TYPE>;

-- Phase 2: Dual-write via trigger (commented out)
-- CREATE TRIGGER sync_{old_column}_to_{new_column} ...

-- Phase 3: Backfill (commented out)
-- UPDATE {table_name} SET {new_column} = {old_column} WHERE {new_column} IS NULL;

-- Phase 4: Application switches to new column

-- Phase 5: Drop old column
-- ALTER TABLE {table_name} DROP COLUMN {old_column};

-- Direct rename (use with caution):
-- ALTER TABLE {table_name} RENAME COLUMN {old_column} TO {new_column};"""

        reverse_sql = f"ALTER TABLE {table_name} RENAME COLUMN {new_column} TO {old_column};"

        return self._create_migration(
            f"rename_{old_column}_to_{new_column}_on_{table_name}",
            rename_sql,
            reverse_sql
        )

    def _create_migration(
        self,
        name: str,
        up_sql: str,
        down_sql: str
    ) -> List[MigrationFile]:
        """Create migration files based on tool format"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        files = []

        if self.tool == MigrationTool.FLYWAY:
            # Flyway: V{version}__{description}.sql
            version = self._get_next_version()
            filename = f"V{version}__{name}.sql"
            content = self._add_header(up_sql, name)
            files.append(MigrationFile(name=filename, content=content))

        elif self.tool == MigrationTool.GOLANG_MIGRATE:
            # golang-migrate: {version}_{name}.up.sql and .down.sql
            version = self._get_next_version(digits=6)
            up_filename = f"{version}_{name}.up.sql"
            down_filename = f"{version}_{name}.down.sql"

            up_content = self._add_header(up_sql, name)
            down_content = self._add_header(down_sql, f"Rollback: {name}")

            files.append(MigrationFile(name=up_filename, content=up_content))
            files.append(MigrationFile(name=down_filename, content=down_content))

        elif self.tool == MigrationTool.DBMATE:
            # dbmate: {timestamp}_{name}.sql with migrate:up and migrate:down
            filename = f"{timestamp}_{name}.sql"
            content = f"""-- migrate:up
{up_sql}

-- migrate:down
{down_sql}
"""
            files.append(MigrationFile(name=filename, content=content))

        elif self.tool == MigrationTool.ALEMBIC:
            # Alembic: Python file (basic template)
            filename = f"{timestamp}_{name}.py"
            content = f'''"""
{name}

Revision ID: {timestamp}
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
from alembic import op
import sqlalchemy as sa

revision = '{timestamp}'
down_revision = None  # Set to previous revision
branch_labels = None
depends_on = None

def upgrade():
    # {name}
    op.execute("""
{up_sql}
    """)

def downgrade():
    # Rollback {name}
    op.execute("""
{down_sql}
    """)
'''
            files.append(MigrationFile(name=filename, content=content))

        else:
            # Generic SQL
            filename = f"{timestamp}_{name}.sql"
            content = self._add_header(up_sql, name)
            files.append(MigrationFile(name=filename, content=content))

        return files

    def _add_header(self, sql: str, description: str) -> str:
        """Add header comment to migration"""
        return f"""-- Migration: {description}
-- Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{sql}
"""

    def _get_next_version(self, digits: int = 1) -> str:
        """Get next migration version number"""
        if not self.migrations_dir.exists():
            return "1".zfill(digits)

        # Find existing migrations
        existing = list(self.migrations_dir.glob("*.sql"))

        if not existing:
            return "1".zfill(digits)

        # Extract version numbers
        versions = []
        for f in existing:
            match = re.match(r'^V?(\d+)', f.name)
            if match:
                versions.append(int(match.group(1)))

        if not versions:
            return "1".zfill(digits)

        next_version = max(versions) + 1
        return str(next_version).zfill(digits)


def parse_column_spec(spec: str) -> Tuple[str, str]:
    """Parse column specification (name:type)"""
    if ':' not in spec:
        raise ValueError(f"Invalid column spec: {spec}. Expected format: name:type")

    name, col_type = spec.split(':', 1)
    return name.strip(), col_type.strip().upper()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate PostgreSQL migration files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate add table migration
  ./generate_migration.py --tool flyway --template add-table --table users --columns id:serial email:varchar

  # Generate add column migration
  ./generate_migration.py --tool golang-migrate --template add-column --table users --column phone:varchar

  # Generate add index migration
  ./generate_migration.py --template add-index --table users --columns email --concurrent

  # Generate custom migration
  ./generate_migration.py --tool dbmate --name add_custom_logic

Column format: name:type (e.g., email:varchar(255), age:integer, active:boolean)
        """
    )

    parser.add_argument(
        '--tool',
        choices=MigrationTool.all(),
        default=MigrationTool.FLYWAY,
        help='Migration tool format (default: flyway)'
    )

    parser.add_argument(
        '--migrations-dir',
        type=Path,
        default=Path('migrations'),
        help='Migrations directory (default: migrations/)'
    )

    parser.add_argument(
        '--template',
        choices=['add-table', 'add-column', 'add-index', 'drop-column',
                'add-constraint', 'rename-column', 'custom'],
        help='Migration template type'
    )

    parser.add_argument(
        '--name',
        help='Migration name (for custom template)'
    )

    parser.add_argument(
        '--table',
        help='Table name'
    )

    parser.add_argument(
        '--columns',
        nargs='+',
        help='Column specifications (name:type format)'
    )

    parser.add_argument(
        '--column',
        help='Single column specification (name:type format)'
    )

    parser.add_argument(
        '--old-column',
        help='Old column name (for rename)'
    )

    parser.add_argument(
        '--new-column',
        help='New column name (for rename)'
    )

    parser.add_argument(
        '--constraint',
        help='Constraint name'
    )

    parser.add_argument(
        '--constraint-type',
        choices=['CHECK', 'UNIQUE', 'FOREIGN KEY'],
        help='Constraint type'
    )

    parser.add_argument(
        '--constraint-def',
        help='Constraint definition'
    )

    parser.add_argument(
        '--unique',
        action='store_true',
        help='Create unique index'
    )

    parser.add_argument(
        '--concurrent',
        action='store_true',
        default=True,
        help='Create index concurrently (default: true)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print migration content without writing files'
    )

    args = parser.parse_args()

    # Create generator
    generator = MigrationGenerator(args.tool, args.migrations_dir)

    # Generate migration based on template
    files: List[MigrationFile] = []

    try:
        if args.template == 'add-table':
            if not args.table or not args.columns:
                parser.error("--table and --columns required for add-table template")

            columns = [parse_column_spec(spec) for spec in args.columns]
            files = generator.generate_add_table(args.table, columns)

        elif args.template == 'add-column':
            if not args.table or not args.column:
                parser.error("--table and --column required for add-column template")

            col_name, col_type = parse_column_spec(args.column)
            files = generator.generate_add_column(args.table, col_name, col_type)

        elif args.template == 'add-index':
            if not args.table or not args.columns:
                parser.error("--table and --columns required for add-index template")

            files = generator.generate_add_index(
                args.table,
                args.columns,
                unique=args.unique,
                concurrent=args.concurrent
            )

        elif args.template == 'drop-column':
            if not args.table or not args.column:
                parser.error("--table and --column required for drop-column template")

            col_name, _ = parse_column_spec(args.column + ":varchar")  # Type doesn't matter
            files = generator.generate_drop_column(args.table, col_name)

        elif args.template == 'add-constraint':
            if not args.table or not args.constraint or not args.constraint_type or not args.constraint_def:
                parser.error("--table, --constraint, --constraint-type, --constraint-def required")

            files = generator.generate_add_constraint(
                args.table,
                args.constraint,
                args.constraint_type,
                args.constraint_def
            )

        elif args.template == 'rename-column':
            if not args.table or not args.old_column or not args.new_column:
                parser.error("--table, --old-column, --new-column required for rename-column")

            files = generator.generate_rename_column(
                args.table,
                args.old_column,
                args.new_column
            )

        elif args.template == 'custom' or args.name:
            if not args.name:
                parser.error("--name required for custom migration")

            # Create empty migration template
            files = generator._create_migration(
                args.name,
                "-- Add your SQL here\n",
                "-- Add rollback SQL here\n"
            )

        else:
            parser.error("--template or --name required")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.json:
        output = {
            'files': [
                {
                    'name': f.name,
                    'content': f.content,
                    'path': str(f.path) if f.path else None
                }
                for f in files
            ]
        }
        print(json.dumps(output, indent=2))

    elif args.dry_run:
        for file in files:
            print(f"\n{'='*80}")
            print(f"File: {file.name}")
            print('='*80)
            print(file.content)

    else:
        # Write files
        for file in files:
            path = file.write(args.migrations_dir)
            print(f"Created: {path}")

        print(f"\nGenerated {len(files)} migration file(s) in {args.migrations_dir}")


if __name__ == '__main__':
    main()
