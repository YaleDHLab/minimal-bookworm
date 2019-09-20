# usage: python utils/process_data "input-texts/*.txt" "input-metadata/*.json"
import glob, json, sys, os, sqlite3, re, uuid, collections, hashlib

txt_files = sys.argv[1]
meta_file = sys.argv[2]
min_count = 1 # minimum count terms need to be retained

# compose a db_name that's a hash of the params used
s = ''.join([str(i) for i in [txt_files, meta_file, min_count]])
try:
  unique_id = hashlib.sha224(s).hexdigest()
except Exception as exc:
  unique_id = hashlib.sha224(s.encode('utf8')).hexdigest()

# build up a dictionary of d[filename] = {'year': ...other meta attrs...}
meta_d = collections.defaultdict()
with open(meta_file) as f:
  j = json.load(f)
  for i in j:
    meta_d[i.get('filename', '')] = i

# build up d[token][year] = word count
years = set()
c = 0
d = collections.defaultdict(collections.Counter)
is_int_like = lambda x: all([i.isnumeric() for i in str(x)])
for i in glob.glob(txt_files):
  filename = os.path.basename(i)
  year = meta_d.get(filename, {}).get('year', False)
  if not year or not is_int_like(year): continue
  year = int(year)
  years.add(year)
  if not year: continue
  with open(i) as f:
    f = f.read().lower() # lowercase
    f = re.sub(r'[^\w\s]', '', f) # remove punct
    for word in f.split():
      d[word][year] += 1
      c += 1

print(' * total tokens:', c)
print(' * total types:', len(d))

db_name = unique_id + '.db'
conn = sqlite3.connect(db_name)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS onegrams
  (token text, year integer, count integer)''')
# insert the data
for word in d:
  for year in d[word]:
    count = d[word][year]
    if count < min_count: continue
    c.execute('INSERT INTO onegrams VALUES ("{}", {}, {})'.format(word, year, count))
conn.commit()

with open('config.json', 'w') as out:
  json.dump({
    'db': db_name,
    'year_min': min(list(years)),
    'year_max': max(list(years)),
    'default_query': ['spring','summer','fall','winter'],
  }, out)