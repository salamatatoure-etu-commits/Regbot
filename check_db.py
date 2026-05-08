# Outil de diagnostic : affiche l'état des chunks dans la base (embeddings générés, indexation).
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(
    dbname=os.getenv('DATABASE_NAME', 'regbot'),
    user=os.getenv('DATABASE_USER', 'postgres'),
    password=os.getenv('DATABASE_PASSWORD', 'Salimata'),
    host=os.getenv('DATABASE_HOST', '127.0.0.1'),
    port=os.getenv('DATABASE_PORT', '5433'),
)
cur = conn.cursor()

# Statistiques globales : total de chunks, ceux avec embedding, ceux marqués indexés
cur.execute("SELECT COUNT(*), COUNT(embedding), COUNT(CASE WHEN is_indexed THEN 1 END) FROM chunk")
total, with_emb, indexed = cur.fetchone()
print(f"Total chunks: {total}, with embedding: {with_emb}, is_indexed: {indexed}")

# Aperçu des 10 premiers documents avec leur nombre de chunks
cur.execute("SELECT c.document_id, d.name, COUNT(*) FROM chunk c JOIN document d ON d.\"documentId\"=c.document_id GROUP BY c.document_id, d.name LIMIT 10")
for row in cur.fetchall():
    print(row)
conn.close()
