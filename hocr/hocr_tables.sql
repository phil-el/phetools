-- Hocr tables.

CREATE TABLE IF NOT EXISTS hocr (
       -- page title, same def as in mw but title are not unique.
       title varchar(255) binary NOT NULL default '',
       --
       lang char(15) binary NOT NULL default '',
       -- SHA-1 content hash in base-16, that's different from mw which use
       -- base 36
       sha1 varbinary(40) NOT NULL default ''
);

CREATE INDEX sha1 ON hocr(sha1);
CREATE UNIQUE INDEX full_title on hocr(lang, title);
