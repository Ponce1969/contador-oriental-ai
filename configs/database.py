
import os

from dotenv import load_dotenv
load_dotenv()

DATABASE = {
    "ENGINE": os.getenv("DB_TYPE", "postgresql"),

    "SQLITE": {
        "PATH": "data/fleting.db"
    },

    "MYSQL": {
        "HOST": "localhost",
        "PORT": 3306,
        "USER": "root",
        "PASSWORD": "",
        "NAME": "fleting",
        "OPTIONS": {
            "charset": "utf8mb4"
        }
    },

    "POSTGRESQL": {
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
        "USER": os.getenv("POSTGRES_USER", "auditor_user"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "NAME": os.getenv("POSTGRES_DB", "auditor_familiar"),
    }
}
