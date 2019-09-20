from flask import Flask, jsonify, request, send_from_directory, g
from collections import defaultdict, Counter
from flask_cors import CORS
import json, os, sqlite3

config = json.load(open('config.json'))
db_file = config['db']

app = Flask(__name__, static_folder='.')
CORS(app)

def get_db():
  db = getattr(g, 'sqlite_database', None)
  if db is None:
    db = g.sqlite_database = sqlite3.connect(db_file)
  return db

def format_series(result, min_year, max_year):
  '''Given a sqlite query result, format a Highcharts series'''
  d = defaultdict(Counter)
  for token, year, count in result:
    d[token][year] = count
  d = dict(d)
  # create response json in Highcharts series form
  d2 = defaultdict(list)
  for token in d:
    for year in range(min_year, max_year, 1):
      d2[token].append(d[token].get(year, None))
  return [{'name': t, 'data': d2[t]} for t in d2]

@app.teardown_appcontext
def close_connection(exception):
  '''Close the sqlite connection when server stops'''
  db = getattr(g, 'sqlite_database', None)
  if db is not None:
    db.close()

@app.route('/api/config')
def get_config():
  '''Return config JSON'''
  return jsonify(config)

@app.route('/api/query')
def get_query():
  '''Return Highcharts data for a query'''
  global config
  min_year = request.args.get('min_year', config['year_min'])
  max_year = request.args.get('max_year', config['year_max'])
  default_query = config['default_query']
  tokens = request.args.getlist('q') if request.args.get('q', False) else default_query
  q =  'SELECT token, year, count '
  q += 'FROM onegrams '
  q += 'WHERE ({}) '.format(' OR '.join(['token=?' for _ in tokens]))
  q += 'AND year>=? '
  q += 'AND year<=? '
  q += 'GROUP BY token, year;'
  cur = get_db().cursor()
  args = [i.lower().strip() for i in tokens] + [int(min_year), int(max_year)]
  cur.execute(q, args)
  result = cur.fetchall()
  return jsonify({
    'min_year': min_year,
    'series': format_series(result, min_year, max_year),
  })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def get_index(path):
  '''Send index.html when users request the base route'''
  return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5050, debug=1)