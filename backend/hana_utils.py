import hana_ml.dataframe as dataframe
from hana_ml.dataframe import ConnectionContext
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

def get_artist_metadata(artist_id) -> dict:
    conn = ConnectionContext(
        address=os.getenv("HANA_HOST"),
        port=int(os.getenv("HANA_PORT")),
        user=os.getenv("HANA_USER"),
        password=os.getenv("HANA_PASSWORD")
    )

    # Force to int just to avoid surprises
    artist_id = int(artist_id)

    sql = f'SELECT * FROM ARTIST_METADATA WHERE "id" = {artist_id}'
    print(f"🚨 Executing Query: {sql}")

    df = conn.sql(sql).collect()

    if df.empty:
        return {}

    row = df.iloc[0]
    return {
        "id": row["id"],
        "name": row["name"],
        "years": row["years"],
        "genre": row["genre"],
        "nationality": row["nationality"],
        "bio": row["bio"],
        "wikipedia": row["wikipedia"],
        "paintings": row["paintings"]
    }

if __name__ == "_main_":
    from pprint import pprint
    pprint(get_artist_metadata(0))