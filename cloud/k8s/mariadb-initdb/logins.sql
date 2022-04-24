create database if not exists logins;
use logins;
create table if not exists logins(
  username varchar(32) primary key,
  password varchar(32));
create user if not exists 'loginuser'@'%' identified by 'loginpass';
grant all privileges on logins.* to 'loginuser'@'%';
