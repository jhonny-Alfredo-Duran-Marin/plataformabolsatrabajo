from sqlalchemy import create_engine, inspect
DATABASE_URL = 'postgresql+psycopg://postgres.etsonjspfydvvqdsappq:BaseDeDatosFicct@aws-0-sa-east-1.pooler.supabase.com:5432/postgres'
engine = create_engine(DATABASE_URL)
inspector = inspect(engine)
for table in ['job_posting', 'screening_question', 'application', 'application_answer']:
    print(f'\n--- {table} ---')
    for col in inspector.get_columns(table):
        print(f"{col['name']} - {col['type']} - Nullable: {col['nullable']}")
