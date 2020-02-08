import json

cookies = json.load(open('cookie.json'))
with open('cookie.txt', 'w') as txt:
  for c in cookies:
    c['expirationDate'] = int(c['expirationDate']) if 'expirationDate' in c else 0
    c['secure'] = 'TRUE' if c['secure'] else 'FALSE'
    txt.write('%(domain)s\tTRUE\t%(path)s\t%(secure)s\t%(expirationDate)d\t%(name)s\t%(value)s\n'
        % c)
