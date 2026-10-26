from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi import Request
from .config import get_settings


def make_engine(url=None, **kwargs):
    args = kwargs.pop('connect_args', {})
    args['options'] = '-ctimezone=UTC ' + args.get('options', '')
    args.setdefault('connect_timeout', 5)
    return create_engine(url or get_settings().database_url, pool_pre_ping=True, hide_parameters=True, connect_args=args, **kwargs)


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False, class_=Session)


def get_db(request: Request):
    with request.app.state.sessions() as session:
        yield session
