-- Jobs table.

-- A cron job use qstat to know running jobs.

-- Jobs in running state but not reported as running by qstat are post
-- checked for success or failure and their state is changed according.

-- Jobs in pending state are started and switched to running state. The cron
-- job only process a fixed amount of row at each run to avoid flooding sge
-- with request. The cron jobs can also decide to limit the total number of
-- jobs started based on cpu_bound field and the actual running jobs.

-- The cron job is intended to run on an exec nodes but
-- https://bugzilla.wikimedia.org/show_bug.cgi?id=54786 block that actually

CREATE TABLE IF NOT EXISTS job (
       -- do not confuse it with sge_jobnumber, this is used to suffix
       -- jobname to form the .err/.out log filename created by sge.
       job_id int unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,
       job_state enum('pending', 'running', 'success', 'accounting',
                      'sge_fail', 'fail') default 'pending',
       -- It's safer to default assign true to this.
       job_cpu_bound bool NOT NULL default 1,
       -- The datetime when the job was added to the jobs table, don't confuse
       -- it with sge submit time.
       job_submit_time int unsigned NOT NULL,
       -- Use distinct jobname for distinct run_cmd so it's easier
       -- to query for example all failed job with a given name.
       job_jobname varchar(31) NOT NULL,
       -- Absolute or $PATH based name are allowed, in any case this cmd
       -- run through jsub except for cmd '@true' and '@false' which are
       -- reserved for debugging purpose.
       job_run_cmd varchar(255) binary NOT NULL,
       -- In MB (1MB = 1024KB and so on)
       job_max_vmem int unsigned NOT NULL,
       -- A json object, only array of strings is allowed. Args are passed to
       -- job_run_cmd as it.
       job_args mediumblob,
       -- Path of the log dir. Must end with a '/', log directory is
       -- automatically created if needed.
       job_log_dir varchar(255) binary NOT NULL,
       -- This is the sha1 sum of job_run_cmd + job_args, indexed so we
       -- we can test if a job has been submited and avoid to resubmit it
       -- Job in success state can always be resubmited, it's up to the run_cmd
       -- tool to check if the job really need to run. FIXME, annoying, for
       -- example if an ocr is asked for a common djvu file and the ocr exist
       -- and is uptodate (File: didn't change) the job will start, will do
       -- nothing but it'll counted as a "new ocr done". The way to circumvent
       -- is to avoid to submit uptodate task.
       job_sha1 varchar(40) binary NOT NULL,
       -- The sge job number, valid only if != 0 and only the sge job number
       -- for the last run. See the accounting table to get all sge job
       -- number for this request.
       sge_jobnumber int unsigned default 0
);

CREATE INDEX job_state ON job(job_state);
CREATE INDEX job_jobname ON job(job_jobname);
CREATE INDEX job_submit_time ON job(job_submit_time);
-- FIXME: do we need this index?
-- CREATE INDEX sge_jobnumber ON job(sge_jobnumber);
CREATE INDEX job_sha1 ON job(job_sha1);

-- As qacct is slow this table is not filled immediatly after a job
-- completion, but deffered through a cron job which use qacct -j pattern -d x
-- to fill the table efficiently.
-- Fields starting with sge_ are identical to the same named field content
-- of qacct -j.
CREATE TABLE IF NOT EXISTS accounting (
       -- Used to retrieve all sge job used to statisfy a request.
       job_id int unsigned NOT NULL,
       sge_jobnumber int unsigned NOT NULL,
       sge_hostname varchar(255) binary NOT NULL default '',
       sge_qsub_time int unsigned default 0,
       sge_start_time int unsigned default 0,
       sge_end_time int unsigned default 0,
       sge_failed int,
       -- name is a bit misleading, it's the exit status of the task.
       sge_exit_status int,
       sge_ru_utime float,
       sge_ru_stime float,
       sge_ru_wallclock float,
       -- In byte, it's not the maxvmem param passed to sge but the maximum
       -- vmem used by the task.
       sge_used_maxvmem bigint unsigned
);

CREATE INDEX job_id ON accounting(job_id);
CREATE INDEX sge_jobnumber ON accounting(sge_jobnumber);
CREATE INDEX sge_hostname ON accounting(sge_hostname);
