"""
Test script for Text-to-SQL functionality
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.common.database_service import db_service
from app.services.text_to_sql_service import text_to_sql_service
from app.config import settings

async def test_text_to_sql():
    """Test the Text-to-SQL service"""
    
    print("=" * 60)
    print("Text-to-SQL Service Test (Mistral via Ollama)")
    print("=" * 60)
    
    try:
        # Initialize service
        print("\n1. Initializing Text-to-SQL service...")
        await text_to_sql_service.initialize()
        print("✅ Service initialized successfully")
        
        # Display schema
        print("\n2. Database Schema:")
        schema = await text_to_sql_service.get_schema_summary()
        for table, info in schema.items():
            print(f"   Table: {table}")
            print(f"   Columns ({info['column_count']}): {', '.join(info['columns'][:5])}")
            if len(info['columns']) > 5:
                print(f"   ... and {len(info['columns']) - 5} more")
        
        # Test queries
        test_queries = [
            "Show me all cities",
            "Get top 10 cities by population",
            "Count total number of cities",
            "Find cities with population over 1 million",
        ]
        
        print("\n3. Testing Natural Language Queries:")
        print("-" * 60)
        
        for idx, query in enumerate(test_queries, 1):
            print(f"\n📝 Query {idx}: {query}")
            print("-" * 40)
            
            try:
                # Generate SQL only (without execution)
                sql = await text_to_sql_service.generate_sql(query)
                print(f"Generated SQL:\n{sql}")
                
                # Validate
                is_valid, msg = text_to_sql_service.validate_sql(sql)
                print(f"\nValidation: {'✅ Valid' if is_valid else '❌ Invalid'} - {msg}")
                
                # If you want to execute (uncomment below):
                # result = await text_to_sql_service.execute_natural_query(query)
                # if result["success"]:
                #     print(f"\n✅ Execution successful!")
                #     print(f"Rows returned: {result['row_count']}")
                #     if result['row_count'] > 0:
                #         print(f"First result: {result['results'][0]}")
                # else:
                #     print(f"❌ Execution failed: {result['error']}")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
            
            print()
        
        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_database_connection():
    """Test 1: Database Connection"""
    print("\n" + "=" * 50)
    print("TEST 1: Database Connection")
    print("=" * 50)

    success = db_service.test_connection()
    if success:
        print("✅ Database connection successful")
        return True
    else:
        print("❌ Database connection failed")
        print("Please check your .env configuration:")
        print(f"  DB_SERVER: {settings.DB_SERVER}")
        print(f"  DB_NAME: {settings.DB_NAME}")
        print(f"  DB_USE_WINDOWS_AUTH: {settings.DB_USE_WINDOWS_AUTH}")
        return False


async def test_schema_retrieval():
    """Test 2: Schema Retrieval"""
    print("\n" + "=" * 50)
    print("TEST 2: Database Schema Retrieval")
    print("=" * 50)

    try:
        schema = await db_service.get_schema_info()
        print(f"✅ Found {len(schema)} tables:")
        for table_name, columns in schema.items():
            print(f"  - {table_name}: {len(columns)} columns")
        return True
    except Exception as e:
        print(f"❌ Schema retrieval failed: {e}")
        return False


async def test_direct_sql():
    """Test 3: Direct SQL Execution"""
    print("\n" + "=" * 50)
    print("TEST 3: Direct SQL Query")
    print("=" * 50)

    query = "SELECT TOP 5 CityID, CityName, Country FROM Cities"
    print(f"Query: {query}")

    try:
        results = await db_service.execute_query(query)
        print(f"✅ Query successful! Retrieved {len(results)} rows:")
        for row in results:
            print(f"  {row}")
        return True
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False


async def test_text_to_sql_init():
    """Test 5: Text-to-SQL Service Initialization"""
    print("\n" + "=" * 50)
    print("TEST 5: Text-to-SQL Service Initialization")
    print("=" * 50)

    try:
        await text_to_sql_service.initialize()
        print("✅ Text-to-SQL service initialized")
        print(f"Schema loaded for {len(text_to_sql_service.schema_context)} tables")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


async def test_sql_generation():
    """Test 6: SQL Generation from Natural Language"""
    print("\n" + "=" * 50)
    print("TEST 6: SQL Generation")
    print("=" * 50)

    test_queries = [
        "Show me all cities in India",
        "List top 10 cities",
        "Find cities in Punjab state",
    ]

    for user_query in test_queries:
        print(f"\nUser Query: '{user_query}'")
        try:
            sql = await text_to_sql_service.generate_sql(user_query)
            print(f"Generated SQL: {sql}")

            # Validate
            is_valid, msg = text_to_sql_service.validate_sql(sql)
            if is_valid:
                print(f"✅ Valid SQL")
            else:
                print(f"⚠️ Validation warning: {msg}")

        except Exception as e:
            print(f"❌ Generation failed: {e}")

    return True

async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 TEXT-TO-SQL SYSTEM TEST SUITE")
    print("=" * 70)

    tests = [
        ("Database Connection", test_database_connection),
        ("Schema Retrieval", test_schema_retrieval),
        ("Direct SQL", test_direct_sql),
        ("Text-to-SQL Init", test_text_to_sql_init),
        ("SQL Generation", test_sql_generation),
        ("Ollama connection", test_text_to_sql)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Your system is ready to use.")
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")


def main():
    """Main entry point"""
    print("Starting Text-to-SQL System Tests...\n")
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
