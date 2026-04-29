from app.db.session import check_database_connection


if __name__ == "__main__":
    result = check_database_connection()
    print(result)
    raise SystemExit(0 if result.get("ok") else 1)
