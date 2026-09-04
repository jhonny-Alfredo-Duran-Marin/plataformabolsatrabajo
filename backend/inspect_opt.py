from sqlalchemy import create_engine, inspect
DATABASE_URL = 'postgresql+psycopg://postgres.etsonjspfydvvqdsappq:BaseDeDatosFicct@aws-0-sa-east-1.pooler.supabase.com:5432/postgres'
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
for col in inspector.get_columns('screening_option'):
    print(f"{col['name']} - {col['type']} - Nullable: {col['nullable']}")
