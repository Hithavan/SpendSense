import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

connection = psycopg2.connect(DATABASE_URL)

print("Connected to Supabase successfully!")

with connection.cursor() as cursor:
	cursor.execute(
		"""
		SELECT table_name
		FROM information_schema.tables
		WHERE table_schema = 'public'
		ORDER BY table_name
		"""
	)
	print("Public tables:", [row[0] for row in cursor.fetchall()])

connection.close()