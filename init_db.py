from storage import init_db

if __name__ == "__main__":
    conn = init_db()
    conn.close()