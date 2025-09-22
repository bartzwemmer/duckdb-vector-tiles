import duckdb
from pathlib import Path

# database_location = "tiles.db"

def init_database(database_location: str) -> None:
    # Create a DuckDB database and load the spatial extension
    if Path(database_location).exists():
        # remove old database file
        Path(database_location).unlink()

    # Initialize a new database
    con = duckdb.connect(database_location, False)

    # Install spatial
    con.execute("INSTALL spatial;")#  from <some path>")
    con.execute("load spatial;")
    con.commit()

    # Load dataset
    data = "rijksmonumenten.geojson"
    con.sql(f"CREATE TABLE IF NOT EXISTS monuments AS SELECT * FROM st_read('{data}');")
    con.commit()
    # DuckDB allows 1 write connection, or multiple read connections
    # So we close this connection after initializing the database
    con.close()

if __name__ == '__main__':
    database_location = "test.db"
    # Some local testing
    init_database(database_location)
    con = duckdb.connect(database_location, True)
    con.execute("load spatial")
    data = con.execute("SELECT * FROM monuments LIMIT 10;")
    print(data.fetchall())
    con.close()