#!/usr/bin/python
import os
from sqlalchemy import *
from sqlalchemy.orm import *

info_keys = ('dbname', 'author', 'version', 'direction', 'origLang', 'destLang',
             'license', 'category', 'description')


def readSqlite(glos, filename=''):
  engine = create_engine('sqlite:///' + filename)
  connection = engine.connect()
  ##########
  result = connection.execute('select * from dbinfo')
  row = result.fetchone()
  for key in info_keys:
    try:
      value = row[key]
    except KeyError:## KeyError?????????
      #if value!='':##???????????
      glos.setInfo(key, value)
  ##########
  result = connection.execute('select * from word')
  d = []
  for row in result:
    ## type(row['wname']) == type(row['wmean']) == unicode
    d.append((row['wname'].encode('utf8'), row['wmean'].encode('utf8')))
  glos.data = d
  ##########
  connection.close()
  return True


class Word(object):
  def __init__(self, s_id=0, wname=u'', wmean=u''):
    self.s_id = s_id
    self.wname = wname
    self.wmean = wmean


class Info(object):
  def __init__(self, dbname, author='', version='', direction='', origLang='',
  destLang='', license='', category='', description=''):
    self.dbname = dbname
    self.author = author
    self.version = version
    self.direction = direction
    self.origLang = origLang
    self.destLang = destLang
    self.license = license
    self.category = category
    self.description = description



def writeSqlite(glos, filename=''):
  if filename=='':
    #filename=self.getInfo('filename')+'.m2'
    filename=glos.filename + '.m2'
  if os.path.exists(filename):
    os.remove(filename)
  engine = create_engine('sqlite:///' + filename)
  metadata = MetaData()
  metadata.bind = engine
  ##########################
  word_table = Table('word', metadata,
    Column('s_id', Integer, primary_key=True),
    Column('wname', Text, nullable=False),
    Column('wmean', Text)
  )
  mapper(Word, word_table)
  ########
  info_table = Table('dbinfo', metadata,
    Column('dbname',      Text, primary_key=True),
    Column('author',      Text),
    Column('version',     Text),
    Column('direction',   Text),
    Column('origLang',    Text),
    Column('destLang',    Text),
    Column('license',     Text),
    Column('category',    Text),
    Column('description', Text)
  )
  mapper(Info, info_table)
  ########
  metadata.create_all()
  ##########################
  d = glos.data
  n = len(d)
  for i in xrange(n):
    #.decode('utf8'),
    word_table.insert().execute(
      wname = d[i][0],
      wmean = d[i][1]
    )
  ########
  info = {}
  for key in info_keys:
    info[key] = glos.getInfo(key)#.decode('utf8')
  info_table.insert().execute(**info)
  ##########################
  return True




