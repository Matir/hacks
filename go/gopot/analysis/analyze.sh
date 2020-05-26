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
update results set country=(select ipdata.ip2asn.country from ipdata.ip2asn join ip_lookup on ip_lookup.ip_idx = ipdata.ip2asn.iplow_n where ip_lookup.ipn=results.ipn),
  asn_num=(select ipdata.ip2asn.asn from ipdata.ip2asn join ip_lookup on ip_lookup.ip_idx = ipdata.ip2asn.iplow_n where ip_lookup.ipn=results.ipn),
  asn_name=(select ipdata.ip2asn.asnname from ipdata.ip2asn join ip_lookup on ip_lookup.ip_idx = ipdata.ip2asn.iplow_n where ip_lookup.ipn=results.ipn);
/* Perform stats */
.headers on
.mode csv
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
.output topips.csv
select remote_ip,count(*) as count from results group by remote_ip order by count desc limit 10;
.output servers.csv
select server,count(*) as count from results group by server;
.output topsubnets.csv
select rtrim(remote_ip, '1234567890') || '0/32' as subnet, count(distinct remote_ip) as num_ips, count(*) as count from results group by subnet order by count desc limit 10;
.output topcountries.csv
select country,count(*) as count from results group by country order by count desc limit 10;
.output topasns.csv
select asn_num,asn_name,count(*) as count from results group by asn_num order by count desc limit 10;
.output torcounts.csv
select count(distinct remote_ip),case tn.ip when remote_ip then 1 else 0 end as is_node from results left join ipdata.tornodes as tn on results.remote_ip = tn.ip group by is_node;
EOSQL

echo 'Build graphs...'
cat <<"EOPY" | python3
import csv
import matplotlib.pyplot as plt

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

EOPY

echo 'Done'
