#!/usr/bin/env python
# encoding: utf-8

import psycopg2
import psycopg2.extras

import settings

def get_db_conn(cursor_dict=False):
    conn=psycopg2.connect(
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASS,
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            cursor_factory=psycopg2.extras.DictCursor if cursor_dict else None
            )
    conn.autocommit=True
    return conn

