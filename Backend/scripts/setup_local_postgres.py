"""Create the local development database/login; never reset existing passwords."""
from getpass import getpass
from pathlib import Path

import psycopg
from psycopg import sql
from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def main():
    env_path = Path(__file__).resolve().parents[1] / '.env'
    url = make_url(dotenv_values(env_path).get('DATABASE_URL', ''))
    if (url.drivername != 'postgresql+psycopg' or url.username != 'travelly_app'
            or url.database != 'travelly_dev' or not url.password
            or url.host not in ('localhost', '127.0.0.1', '::1')):
        raise ValueError('Backend/.env must specify local PostgreSQL, travelly_dev and travelly_app with a password.')

    admin = input('PostgreSQL administrator username [postgres]: ').strip() or 'postgres'
    password = getpass('PostgreSQL administrator password (not stored): ')
    options = dict(host=url.host, port=url.port or 5432, user=admin,
                   password=password, connect_timeout=5, autocommit=True)
    with psycopg.connect(dbname='postgres', **options) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = %s', (url.username,))
            role = cursor.fetchone()
            if role is None:
                cursor.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}').format(
                    sql.Identifier(url.username), sql.Literal(url.password)))
                print('Created travelly_app with the password from Backend/.env.')
            elif not role[0] or any(role[1:]):
                raise RuntimeError('Existing travelly_app must be a login without administrator privileges. No role changes were made.')
            else:
                print('travelly_app already exists; its password was not changed.')

            cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (url.database,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
                    sql.Identifier(url.database), sql.Identifier(url.username)))
                print('Created travelly_dev owned by travelly_app.')
            cursor.execute(sql.SQL('GRANT CONNECT, CREATE ON DATABASE {} TO {}').format(
                sql.Identifier(url.database), sql.Identifier(url.username)))

    with psycopg.connect(dbname=url.database, **options) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL('GRANT USAGE, CREATE ON SCHEMA public TO {}').format(sql.Identifier(url.username)))
    with psycopg.connect(host=url.host, port=url.port or 5432, dbname=url.database,
                        user=url.username, password=url.password, connect_timeout=5):
        print('PASS: travelly_app can connect to travelly_dev. Run the Alembic migration next.')


if __name__ == '__main__':
    try:
        main()
    except (psycopg.Error, ValueError, RuntimeError):
        # Driver messages can include SQL or connection details; do not print them.
        print('FAIL: setup did not finish. Check administrator credentials/permissions and the app password in Backend/.env. Existing role passwords were not changed.')
        raise SystemExit(1) from None
