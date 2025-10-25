"""
Test database migrations and table existence.

Verifies that all required tables exist for the enhanced workflow.
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


def test_database_migrations():
    """Test that all database migrations are applied."""
    print("=" * 60)
    print("🗄️  DATABASE MIGRATIONS TEST")
    print("=" * 60)

    # Get database URL
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("\n❌ DATABASE_URL not set in .env")
        return False

    print(f"\n📋 Database URL: {database_url[:30]}...")

    # Required tables for enhanced workflow
    required_tables = [
        "conversations",
        "messages",
        "gdpr_deletions",  # From migration 001
        "gdpr_exports",    # From migration 001
        "escalations",     # From migration 003
        "rag_cache",      # From migration 004
        "lead_scores"     # From migration 005 (NEW)
    ]

    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("\n✅ Connected to database")

        # Check each table
        print("\n" + "=" * 60)
        print("Checking required tables...")
        print("=" * 60)

        all_exist = True
        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                );
            """, (table,))

            exists = cursor.fetchone()[0]

            if exists:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"✅ {table:<20} (rows: {count})")
            else:
                print(f"❌ {table:<20} MISSING!")
                all_exist = False

        # Check lead_scores table structure
        if all_exist:
            print("\n" + "=" * 60)
            print("Verifying lead_scores table structure...")
            print("=" * 60)

            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'lead_scores'
                ORDER BY ordinal_position;
            """)

            columns = cursor.fetchall()
            print(f"\n✅ lead_scores has {len(columns)} columns:")
            for col_name, col_type in columns:
                print(f"   - {col_name:<30} {col_type}")

            # Check indexes
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'lead_scores';
            """)

            indexes = cursor.fetchall()
            print(f"\n✅ lead_scores has {len(indexes)} index(es):")
            for (idx_name,) in indexes:
                print(f"   - {idx_name}")

            # Check view exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views
                    WHERE table_name = 'latest_lead_scores'
                );
            """)

            view_exists = cursor.fetchone()[0]
            if view_exists:
                print("\n✅ View 'latest_lead_scores' exists")
            else:
                print("\n⚠️  View 'latest_lead_scores' not found")

        cursor.close()
        conn.close()

        if all_exist:
            print("\n" + "=" * 60)
            print("✅ ALL MIGRATIONS APPLIED")
            print("=" * 60)
            print("\n🎉 Database is ready for Phase 4 testing!")
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ MISSING TABLES")
            print("=" * 60)
            print("\n💡 Run migrations:")
            print("   cd migrations && psql $DATABASE_URL -f 001_gdpr_tables.sql")
            print("   cd migrations && psql $DATABASE_URL -f 003_add_escalations_table.sql")
            print("   cd migrations && psql $DATABASE_URL -f 004_add_rag_cache_table.sql")
            print("   cd migrations && psql $DATABASE_URL -f 005_add_lead_scores_table.sql")
            return False

    except psycopg2.OperationalError as e:
        print(f"\n❌ Cannot connect to database: {e}")
        print("\n💡 Tips:")
        print("   - Check DATABASE_URL in .env")
        print("   - Ensure database is running")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = test_database_migrations()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
