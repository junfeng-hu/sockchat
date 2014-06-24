#!/usr/bin/env python
# encoding: utf-8

from sqlalchemy import create_engine

engine = create_engine('postgresql://junfeng7@localhost/socketchat', echo=True)

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from sqlalchemy import Column, Integer, String

class User(Base):
     __tablename__ = 'users'

     id = Column(Integer, primary_key=True)
     name = Column(String, unique=True)
     password = Column(String)

     def __repr__(self):
        return "<User(name='%s', password='%s')>" % (
                             self.name, self.password)

if __name__ == "__main__":
    Base.metadata.create_all(engine)
