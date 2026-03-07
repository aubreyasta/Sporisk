"""
SporaSync — MongoDB Atlas (mongo.py)
======================================
Identical to db.py but with the macOS SSL fix built in.

pip install pymongo certifi
python mongo.py
"""

import os
import ssl
import certifi
import pandas as pd
from pymongo import MongoClient, GEOSPHERE, ASCENDING, DESCENDING
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from datetime import datetime, timedelta

MONGO_URI = "mongodb+srv://maryaputra_db_user:WdhCC32uvySP2FQL@mercedhack.q4ptgw0.mongodb.net/"


DB_NAME = "sporasync"


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION — certifi fixes macOS SSL certificate verify failed
# ─────────────────────────────────────────────────────────────────────────────

def get_client():
    return MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000,
        tls=True,
        tlsCAFile=certifi.where(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────

class SporaSyncDB:

    def __init__(self):
        self.client = get_client()
        self.db     = self.client[DB_NAME]
        # Ping to verify connection before doing anything
        self.client.admin.command("ping")
        print(f"✅ Connected to MongoDB Atlas → '{DB_NAME}'")
        self._setup_indexes()

    # ─────────────────────────────────────────────────────────────────────
    # INDEXES
    # ─────────────────────────────────────────────────────────────────────

    def _setup_indexes(self):
        print("  Setting up indexes...")

        self.db.risk_scores.create_index(
            [("county", ASCENDING), ("date", DESCENDING)],
            unique=True, name="county_date_unique"
        )
        self.db.risk_scores.create_index(
            [("location", GEOSPHERE)], name="location_2dsphere"
        )
        self.db.weather.create_index(
            [("county", ASCENDING), ("date", DESCENDING)],
            unique=True, name="county_date_unique"
        )
        self.db.air_quality.create_index(
            [("county", ASCENDING), ("date", DESCENDING)],
            unique=True, name="county_date_unique"
        )
        self.db.cases.create_index(
            [("county", ASCENDING), ("year", ASCENDING)],
            unique=True, name="county_year_unique"
        )
        # TTL — auto-delete alerts after 7 days
        self.db.alerts.create_index(
            "created_at", expireAfterSeconds=604800, name="ttl_7days"
        )
        print("  ✅ Indexes ready")

    # ─────────────────────────────────────────────────────────────────────
    # PUSH DATA
    # ─────────────────────────────────────────────────────────────────────

    def push_master_csv(self, csv_path: str = "data/sporasync_master.csv"):
        print(f"\n━━ Pushing {csv_path} to Atlas ━━")
        df = pd.read_csv(csv_path, parse_dates=["date"])
        print(f"  Loaded {len(df):,} rows")

        self._push_weather(df)
        self._push_air_quality(df)
        self._push_risk_scores(df)

        if os.path.exists("data/cases.csv"):
            self._push_cases(pd.read_csv("data/cases.csv"))

        print("\n✅ All data pushed to Atlas")
        self._print_counts()

    def _upsert(self, col_name: str, docs: list, keys: list):
        col = self.db[col_name]
        ops = [
            UpdateOne({k: d[k] for k in keys}, {"$set": d}, upsert=True)
            for d in docs
        ]
        try:
            r = col.bulk_write(ops, ordered=False)
            print(f"  [{col_name}] upserted={r.upserted_count} modified={r.modified_count}")
        except BulkWriteError as e:
            print(f"  ⚠ {col_name}: {e.details.get('nInserted',0)} inserted with errors")

    def _rows_to_docs(self, df: pd.DataFrame, cols: list) -> list:
        sub = df[[c for c in cols if c in df.columns]].copy()
        docs = []
        for _, row in sub.iterrows():
            d = row.dropna().to_dict()
            if "date" in d:
                d["date"] = pd.Timestamp(d["date"]).to_pydatetime()
            docs.append(d)
        return docs

    def _push_weather(self, df):
        cols = ["date","county","fips","lat","lon",
                "precip_mm","soil_moisture_m3m3","wind_speed_kmh"]
        docs = self._rows_to_docs(df.drop_duplicates(["date","county"]), cols)
        self._upsert("weather", docs, ["county","date"])

    def _push_air_quality(self, df):
        cols = ["date","county","fips","pm10_ugm3","pm10_lag1mo"]
        docs = self._rows_to_docs(df.drop_duplicates(["date","county"]), cols)
        self._upsert("air_quality", docs, ["county","date"])

    def _push_risk_scores(self, df):
        cols = ["date","county","fips","lat","lon",
                "G_pot","E_risk","risk_score","risk_level","risk_color",
                "n_sm_lag6mo","n_precip_lag1p5y","n_pm10_lag1mo",
                "n_soil_aridity","n_wind_speed_kmh"]
        sub = df.drop_duplicates(["date","county"])
        docs = []
        for _, row in sub[[c for c in cols if c in sub.columns]].iterrows():
            d = row.dropna().to_dict()
            d["date"] = pd.Timestamp(d["date"]).to_pydatetime()
            # GeoJSON Point for 2dsphere geospatial queries
            d["location"] = {
                "type": "Point",
                "coordinates": [float(d["lon"]), float(d["lat"])]
            }
            docs.append(d)
        self._upsert("risk_scores", docs, ["county","date"])

    def _push_cases(self, cases_df):
        docs = cases_df.to_dict(orient="records")
        for d in docs:
            d["year"]       = int(d.get("year", 0))
            d["case_count"] = int(d.get("case_count", 0))
        self._upsert("cases", docs, ["county","year"])

    # ─────────────────────────────────────────────────────────────────────
    # QUERIES (what Streamlit calls)
    # ─────────────────────────────────────────────────────────────────────

    def get_latest_risk(self) -> list:
        """Most recent risk score per county, sorted highest risk first."""
        pipeline = [
            {"$sort": {"date": -1}},
            {"$group": {
                "_id":        "$county",
                "county":     {"$first": "$county"},
                "date":       {"$first": "$date"},
                "risk_score": {"$first": "$risk_score"},
                "risk_level": {"$first": "$risk_level"},
                "risk_color": {"$first": "$risk_color"},
                "G_pot":      {"$first": "$G_pot"},
                "E_risk":     {"$first": "$E_risk"},
                "lat":        {"$first": "$lat"},
                "lon":        {"$first": "$lon"},
                "fips":       {"$first": "$fips"},
            }},
            {"$sort": {"risk_score": -1}},
        ]
        return list(self.db.risk_scores.aggregate(pipeline))

    def get_risk_history(self, county: str, days: int = 365) -> list:
        """Daily risk scores for one county over the past N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return list(
            self.db.risk_scores
            .find(
                {"county": county, "date": {"$gte": cutoff}},
                {"_id":0,"date":1,"risk_score":1,"G_pot":1,"E_risk":1,"risk_level":1}
            )
            .sort("date", ASCENDING)
        )

    def get_county_comparison(self) -> list:
        """Average + max risk per county across all time — powers the heatmap."""
        pipeline = [
            {"$group": {
                "_id":        "$county",
                "avg_risk":   {"$avg": "$risk_score"},
                "max_risk":   {"$max": "$risk_score"},
                "avg_G_pot":  {"$avg": "$G_pot"},
                "avg_E_risk": {"$avg": "$E_risk"},
                "lat":        {"$first": "$lat"},
                "lon":        {"$first": "$lon"},
                "fips":       {"$first": "$fips"},
            }},
            {"$sort": {"avg_risk": -1}},
        ]
        return list(self.db.risk_scores.aggregate(pipeline))

    def get_seasonal_trend(self, county: str) -> list:
        """Average risk by calendar month — reveals the seasonal blow pattern."""
        pipeline = [
            {"$match": {"county": county}},
            {"$group": {
                "_id":      {"$month": "$date"},
                "avg_risk": {"$avg": "$risk_score"},
                "avg_pm10": {"$avg": "$n_pm10_lag1mo"},
                "avg_Gpot": {"$avg": "$G_pot"},
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "month":    "$_id",
                "avg_risk": {"$round":["$avg_risk",1]},
                "avg_pm10": {"$round":["$avg_pm10",3]},
                "avg_Gpot": {"$round":["$avg_Gpot",3]},
                "_id": 0
            }},
        ]
        return list(self.db.risk_scores.aggregate(pipeline))

    def get_counties_near(self, lat: float, lon: float, radius_km: float = 100) -> list:
        """Geospatial — counties within radius_km of a coordinate (e.g. from ZIP)."""
        return list(
            self.db.risk_scores.find(
                {"location": {"$nearSphere": {
                    "$geometry": {"type":"Point","coordinates":[lon,lat]},
                    "$maxDistance": radius_km * 1000
                }}},
                {"_id":0,"county":1,"risk_score":1,"risk_level":1,"date":1}
            ).limit(8)
        )

    def get_high_risk_days(self, threshold: float = 60.0) -> list:
        """All county-days where risk exceeded the threshold."""
        return list(
            self.db.risk_scores
            .find(
                {"risk_score": {"$gte": threshold}},
                {"_id":0,"county":1,"date":1,"risk_score":1,"risk_level":1}
            )
            .sort([("risk_score", DESCENDING),("date", DESCENDING)])
            .limit(100)
        )

    # ─────────────────────────────────────────────────────────────────────
    # ALERTS (TTL collection — auto-expires after 7 days)
    # ─────────────────────────────────────────────────────────────────────

    def create_alert(self, county: str, risk_score: float,
                     risk_level: str, message: str) -> str:
        doc = {
            "county":     county,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "message":    message,
            "created_at": datetime.utcnow(),
        }
        return str(self.db.alerts.insert_one(doc).inserted_id)

    def get_active_alerts(self) -> list:
        return list(
            self.db.alerts.find({}, {"_id":0}).sort("created_at", DESCENDING)
        )

    def seed_alerts_from_risk(self, threshold: float = 65.0):
        """Auto-generate alerts for any county currently above threshold."""
        count = 0
        for doc in self.get_latest_risk():
            if doc.get("risk_score", 0) >= threshold:
                self.create_alert(
                    doc["county"], doc["risk_score"], doc["risk_level"],
                    f"{doc['county']} County is at {doc['risk_level']} risk "
                    f"(score: {doc['risk_score']:.1f}/100). "
                    f"Limit outdoor exposure and consider wearing an N95."
                )
                count += 1
        print(f"  🔔 Seeded {count} alerts (threshold={threshold})")

    # ─────────────────────────────────────────────────────────────────────
    # CHANGE STREAM — real-time updates for Streamlit
    # ─────────────────────────────────────────────────────────────────────

    def watch_risk_updates(self, callback):
        """
        Opens a Change Stream on risk_scores. Calls callback(doc) on every insert/update.
        Run in a background thread:
            import threading
            t = threading.Thread(target=db.watch_risk_updates, args=(my_fn,), daemon=True)
            t.start()
        """
        print("  👁 Watching risk_scores for live changes...")
        with self.db.risk_scores.watch(
            [{"$match": {"operationType": {"$in": ["insert","update","replace"]}}}]
        ) as stream:
            for change in stream:
                callback(change.get("fullDocument", {}))

    # ─────────────────────────────────────────────────────────────────────
    # UTILS
    # ─────────────────────────────────────────────────────────────────────

    def _print_counts(self):
        print("\n  📊 Atlas Collection Counts:")
        for col in ["weather","air_quality","risk_scores","cases","alerts"]:
            print(f"    {col:15s}: {self.db[col].count_documents({}):,} docs")

    def close(self):
        self.client.close()


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db = SporaSyncDB()

    db.push_master_csv("data/sporasync_master.csv")
    db.seed_alerts_from_risk(threshold=65.0)

    print("\n━━ Latest risk per county ━━")
    for d in db.get_latest_risk():
        print(f"  {d['county']:12s} → {d['risk_score']:5.1f}  [{d['risk_level']}]")

    print("\n━━ County comparison ━━")
    for d in db.get_county_comparison():
        print(f"  {d['_id']:12s} → avg={d['avg_risk']:.1f}  max={d['max_risk']:.1f}")

    print("\n━━ Seasonal trend (Fresno) ━━")
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    for d in db.get_seasonal_trend("Fresno"):
        print(f"  {months[d['month']-1]}: {d['avg_risk']}")

    print("\n━━ Counties near Merced ━━")
    for d in db.get_counties_near(lat=37.30, lon=-120.48, radius_km=150):
        print(f"  {d['county']:12s} → {d.get('risk_score','?')}")

    print("\n━━ Active alerts ━━")
    for a in db.get_active_alerts():
        print(f"  [{a['risk_level']}] {a['county']}: {a['message'][:80]}...")

    db.close()