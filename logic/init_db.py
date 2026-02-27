import os
import psycopg2
from psycopg2.extras import RealDictCursor
from database import get_db_connection

def init_tables():
    """Creates all required tables in the Neon database."""
    sql = """
    CREATE TABLE IF NOT EXISTS resultados (
        id SERIAL PRIMARY KEY,
        fecha TEXT,
        fecha_iso DATE,
        loteria TEXT,
        horario_sorteo TEXT,
        animalito_ganador TEXT,
        fecha_creacion TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(fecha, loteria, horario_sorteo)
    );

    CREATE TABLE IF NOT EXISTS evaluacion_pronosticos (
        id SERIAL PRIMARY KEY,
        fecha_evaluacion TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        loteria TEXT,
        horario_sorteo TEXT,
        fecha_sorteo TEXT,
        pronosticos_generados TEXT,
        resultado_real TEXT,
        aciertos INTEGER,
        total_pronosticos INTEGER,
        efectividad REAL,
        metodos_utilizados TEXT
    );

    CREATE TABLE IF NOT EXISTS scraping_log (
        id SERIAL PRIMARY KEY,
        fecha_hora TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        loteria TEXT,
        resultados_obtenidos INTEGER,
        resultados_cargados INTEGER,
        estado TEXT,
        detalles TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_fecha_iso ON resultados(fecha_iso);
    CREATE INDEX IF NOT EXISTS idx_loteria ON resultados(loteria);
    CREATE INDEX IF NOT EXISTS idx_fecha_loteria ON resultados(fecha_iso, loteria);
    """
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            print("[SUCCESS] All tables created successfully.")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to create tables: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        print("[ERROR] Could not connect to the database.")

if __name__ == "__main__":
    init_tables()
