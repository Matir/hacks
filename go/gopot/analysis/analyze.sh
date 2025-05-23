#!/bin/bash

if test -f scp.sh ; then
  bash scp.sh
fi

rm collected.db
echo 'Merge collected data...'
echo 'create table results (username TEXT, password TEXT, timestamp TEXT, remote_ip TEXT, remote_port INTEGER, client TEXT, server TEXT);' \
  | sqlite3 collected.db
for db in server*.db ; do
  (
    echo "attach database '${db}' as imp;"
    echo "insert into results SELECT * FROM imp.results JOIN (select '${db}' as server);"
  ) \
    | sqlite3 collected.db
done

echo 'Start analysis...'
cat <<"EOSQL" | sqlite3 collected.db
.load ./sqlite3-inet/libsqliteipv4
attach database 'ip2asn.db' as ipdata;

/* Build indexes */
create index username_idx on results(username);
create index password_idx on results(password);
create index timestamp_idx on results(timestamp);
create index remote_ip_idx on results(remote_ip);

/* Update records */
alter table results add column asn_num TEXT;
alter table results add column asn_name TEXT;
alter table results add column country TEXT;
alter table results add column ipn INT;
update results set ipn = IP2INT(remote_ip);
create index ipn_idx on results(ipn);
create temporary table ip_lookup as select distinct results.ipn as ipn, (select
  ipdata.ip2asn.iplow_n from ipdata.ip2asn where ipn >= ipdata.ip2asn.iplow_n
  order by ipdata.ip2asn.iplow_n desc limit 1) as ip_idx from results;
create index ip_lookup_ipn_idx on ip_lookup(ipn);
update results set country=(select ipdata.ip2asn.country from ipdata.ip2asn join ip_lookup on ip_lookup.ip_idx = ipdata.ip2asn.iplow_n where ip_lookup.ipn=results.ipn),
  asn_num=(select ipdata.ip2asn.asn from ipdata.ip2asn join ip_lookup on ip_lookup.ip_idx = ipdata.ip2asn.iplow_n where ip_lookup.ipn=results.ipn),
  asn_name=(select ipdata.ip2asn.asnname from ipdata.ip2asn join ip_lookup on ip_lookup.ip_idx = ipdata.ip2asn.iplow_n where ip_lookup.ipn=results.ipn);
create index country_idx on results(country);
create index asn_name_idx on results(asn_name);
create index asn_num_idx on results(asn_num);

/* Perform stats */
.headers on
.mode csv
.output count.csv
select count(*) as count from results;
.output topusers.csv
select username,count(*) as count from results group by username order by count desc limit 10;
.output toppass.csv
select password,count(*) as count from results group by password order by count desc limit 10;
.output topcreds.csv
select username,password,count(*) as count from results group by username,password order by count desc limit 10;
.output topclients.csv
select client,count(*) as count from results group by client order by count desc limit 10;
.output days_of_week.csv
select strftime('%w', timestamp) as dow_num, CASE strftime('%w', timestamp) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END as dow, count(*) as count from results group by dow_num order by dow_num asc;
.output hours.csv
select strftime('%H', timestamp) as hour, count(*) as count from results group by hour order by hour asc;
.output allips.csv
select remote_ip,count(*) as count from results group by remote_ip order by count desc;
.output topips.csv
select remote_ip,count(*) as count from results group by remote_ip order by count desc limit 10;
.output servers.csv
select server,count(*) as count from results group by server;
.output topsubnets.csv
select rtrim(remote_ip, '1234567890') || '0/32' as subnet, count(distinct remote_ip) as num_ips, count(*) as count from results group by subnet order by count desc limit 10;
.output topcountries.csv
select country,count(*) as count from results group by country order by count desc limit 10;
.output allcountries.csv
select country,count(*) as count from results group by country order by count desc;
.output topasns.csv
select asn_num,asn_name,count(*) as count from results group by asn_num order by count desc limit 10;
.output allasns.csv
select asn_name,country,asn_num,count(*) as count from results group by asn_num order by count desc;
.output torcounts.csv
select count(distinct remote_ip) as count,case tn.ip when remote_ip then 1 else 0 end as is_node from results left join ipdata.tornodes as tn on results.remote_ip = tn.ip group by is_node;
.output dates.csv
select count(*) as count, date(timestamp) as date from results where timestamp >= '2020-06-01' group by date order by date asc;
EOSQL

echo 'Build graphs...'
cat <<"EOPY" | python3
import csv
import matplotlib.pyplot as plt
import numpy as np

for l in csv.DictReader(open('count.csv')):
  total_count = int(l['count'])

rows = [i for i in csv.DictReader(open('hours.csv'))]
x = [int(r['hour']) for r in rows]
y = [int(r['count']) for r in rows]
plt.title("Attempts by Hour of Day")
plt.bar(x, y)
plt.xlabel("Hour of Day (UTC)")
plt.ylabel("Count")
plt.xticks([0, 6, 12, 18, 24])
plt.savefig('hours.png')
plt.clf()

with open('hours.md', 'w') as tbl:
  print('|{:->4s}|{:->8s}|'.format('-', '-'), file=tbl)
  print('|{: >4s}|{: >8s}|'.format('Hour', 'Count'), file=tbl)
  print('|{:->4s}|{:->8s}|'.format('-', '-'), file=tbl)
  for r in rows:
    print('|  {hour:>2s}| {count:>7s}|'.format(**r), file=tbl)
  print('|{:->4s}|{:->8s}|'.format('-', '-'), file=tbl)

rows = [i for i in csv.DictReader(open('days_of_week.csv'))]
x = [int(r['dow_num']) for r in rows]
y = [int(r['count']) for r in rows]
plt.title("Attempts by Day of Week")
plt.bar(x, y)
plt.xlabel("Day of Week (UTC)")
plt.ylabel("Count")
plt.xticks(x, [r['dow'] for r in rows])
plt.savefig('days_of_week.png')
plt.clf()

with open('days_of_week.md', 'w') as tbl:
  print('|{:->10s}|{:->8s}|'.format('-', '-'), file=tbl)
  print('|{: >10s}|{: >8s}|'.format('Day', 'Count'), file=tbl)
  print('|{:->10s}|{:->8s}|'.format('-', '-'), file=tbl)
  for r in rows:
    dow = {
      0: 'Sunday',
      1: 'Monday',
      2: 'Tuesday',
      3: 'Wednesday',
      4: 'Thursday',
      5: 'Friday',
      6: 'Saturday',
    }[int(r['dow_num'])]
    print('| {dow:>9s}| {count:>7s}|'.format(dow=dow, count=r['count']), file=tbl)
  print('|{:->10s}|{:->8s}|'.format('-', '-'), file=tbl)

pairs = []
for i, r in enumerate(csv.DictReader(open('allcountries.csv'))):
  if i > 7:
    break
  if float(r['count'])/total_count < 0.01:
    break
  pairs.append((r['country'], int(r['count'])))

pairs.append(('Other', total_count-sum([x[1] for x in pairs])))
plt.title("Source Countries")
plt.pie([x[1] for x in pairs], labels=[x[0] for x in pairs], shadow=True,
  autopct='%0.01f%%', pctdistance=0.8, startangle=90, counterclock=False)
plt.savefig('countries.png')
plt.clf()

with open('topcountries.md', 'w') as tbl:
  print('|{:->10s}|{:->8s}|'.format('-', '-'), file=tbl)
  print('|{: >10s}|{: >8s}|'.format('Country', 'Count'), file=tbl)
  print('|{:->10s}|{:->8s}|'.format('-', '-'), file=tbl)
  for r in csv.DictReader(open('topcountries.csv')):
    print('| {country:>9s}| {count:>7s}|'.format(**r), file=tbl)
  print('|{:->10s}|{:->8s}|'.format('-', '-'), file=tbl)

pairs = []
for i, r in enumerate(csv.DictReader(open('allasns.csv'))):
  if i > 7:
    break
  if float(r['count'])/total_count < 0.01:
    break
  name = '{} ({})'.format(r['asn_name'][:10], r['asn_num'])
  pairs.append((name, int(r['count'])))

pairs.append(('Other', total_count-sum([x[1] for x in pairs])))
plt.title("Source Autonomous System (AS)")
plt.pie([x[1] for x in pairs], labels=[x[0] for x in pairs], shadow=True,
  labeldistance=1.1, autopct='%0.01f%%', pctdistance=0.8, startangle=90,
  counterclock=False)
plt.savefig('asns.png')
plt.clf()

vals = []
labels = []
for r in csv.DictReader(open('torcounts.csv')):
  vals.append(int(r['count']))
  if r['is_node'] == '1':
    labels.append('Tor')
  else:
    labels.append('Non-Tor')

plt.title("Tor Usage")
plt.pie(vals, labels=labels, shadow=True,
  labeldistance=1.1, autopct='%0.01f%%', pctdistance=0.8, startangle=90,
  counterclock=False)
plt.savefig('tor.png')
plt.clf()

rows = [i for i in csv.DictReader(open('dates.csv'))]
x = range(len(rows))
y = [int(r['count']) for r in rows]
plt.title("Attempts by Day")
plt.bar(x, y, width=0.5)
plt.xlabel("Day (UTC)")
plt.ylabel("Count")
plt.savefig('dates.png', dpi=300)
plt.clf()

cnts = [int(i['count']) for i in csv.DictReader(open('allips.csv'))]
plt.title("IPs vs Requests")
plt.xscale('log')
plt.xlabel('Requests')
plt.ylabel('Number of IPs')
nbins = 100
bins = np.logspace(0, np.log10(max(cnts)*1.1), nbins)
ibins = sorted(set([int(a) for a in bins]))
plt.hist(cnts, bins=ibins, log=True)
plt.savefig('ipcnts.png')
plt.clf()

EOPY

echo 'Done'
