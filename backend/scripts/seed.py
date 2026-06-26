"""Seed the platform with demo data.

Creates users + website/file rows. By default it only ENQUEUES a few real
analysis jobs, because each one calls the OpenAI API (costs money/quota).
Bump --enqueue / --files to push more load through the pipeline.

Run inside the api container:
    docker compose exec api python -m scripts.seed
    docker compose exec api python -m scripts.seed --users 100 --enqueue 10 --files 5
"""

import argparse
from urllib.parse import urlparse

from sqlalchemy import text

from app.core.security import hash_password
from app.db.init_db import init_db
from app.db.models import File, Job, JobStatus, JobType, User, Website
from app.db.session import SessionLocal
from app.services import storage, tasks

SAMPLE_URLS = [
    "https://www.python.org",
    "https://fastapi.tiangolo.com",
    "https://kafka.apache.org",
    "https://redis.io",
    "https://docs.celeryq.dev",
    "https://www.docker.com",
    "https://kubernetes.io",
    "https://openai.com",
    "https://www.postgresql.org",
    "https://prometheus.io",
    "https://grafana.com",
    "https://min.io",
    "https://konghq.com",
    "https://nginx.org",
    "https://nodejs.org",
    "https://react.dev",
    "https://vuejs.org",
    "https://angular.dev",
    "https://svelte.dev",
    "https://tailwindcss.com",
    "https://www.typescriptlang.org",
    "https://www.npmjs.com",
    "https://pypi.org",
    "https://github.com",
    "https://about.gitlab.com",
    "https://bitbucket.org",
    "https://stackoverflow.com",
    "https://developer.mozilla.org",
    "https://www.wikipedia.org",
    "https://www.mozilla.org",
    "https://www.cloudflare.com",
    "https://aws.amazon.com",
    "https://azure.microsoft.com",
    "https://cloud.google.com",
    "https://vercel.com",
    "https://www.netlify.com",
    "https://www.heroku.com",
    "https://www.digitalocean.com",
    "https://www.linode.com",
    "https://fly.io",
    "https://supabase.com",
    "https://firebase.google.com",
    "https://auth0.com",
    "https://stripe.com",
    "https://www.twilio.com",
    "https://sendgrid.com",
    "https://slack.com",
    "https://zoom.us",
    "https://www.atlassian.com",
    "https://www.notion.so",
    "https://airtable.com",
    "https://asana.com",
    "https://monday.com",
    "https://www.hubspot.com",
    "https://www.salesforce.com",
    "https://www.shopify.com",
    "https://wordpress.org",
    "https://www.drupal.org",
    "https://www.elastic.co",
    "https://www.datadoghq.com",
    "https://sentry.io",
    "https://newrelic.com",
    "https://www.hashicorp.com",
    "https://www.ansible.com",
    "https://www.jenkins.io",
    "https://circleci.com",
    "https://www.travis-ci.com",
    "https://buildkite.com",
    "https://www.databricks.com",
    "https://www.snowflake.com",
    "https://www.getdbt.com",
    "https://spark.apache.org",
    "https://airflow.apache.org",
    "https://www.rabbitmq.com",
    "https://www.mongodb.com",
    "https://www.mysql.com",
    "https://mariadb.org",
    "https://sqlite.org",
    "https://clickhouse.com",
    "https://www.confluent.io",
    "https://www.elastic.co/kibana",
    "https://www.tableau.com",
    "https://powerbi.microsoft.com",
    "https://www.figma.com",
    "https://miro.com",
    "https://www.canva.com",
    "https://www.adobe.com",
    "https://www.dropbox.com",
    "https://www.box.com",
    "https://www.okta.com",
    "https://www.cloudflare.com/products/zero-trust",
    "https://letsencrypt.org",
    "https://www.w3.org",
    "https://www.ietf.org",
    "https://www.linuxfoundation.org",
    "https://www.ubuntu.com",
    "https://www.redhat.com",
    "https://www.debian.org",
    "https://www.alpinelinux.org",
    "https://helm.sh",
    "https://argo-cd.readthedocs.io",
    "https://opentelemetry.io",
]


def reset_demo_data(db) -> None:
    tasks.celery.control.purge()
    db.execute(text(
        "TRUNCATE TABLE analysis_results, notifications, audit_logs, jobs, "
        "files, websites, users RESTART IDENTITY CASCADE"
    ))
    db.commit()
    print("reset: cleared users, websites, files, jobs, results, notifications, audit logs, and queued Celery messages")


def seed(users: int, websites: int, enqueue: int, files: int, reset: bool) -> None:
    init_db()
    db = SessionLocal()
    try:
        if reset:
            reset_demo_data(db)

        # --- users ---
        created_users = []
        for i in range(users):
            email = f"user{i:03d}@example.com"
            role = "admin" if i == 0 else "user"
            existing = db.query(User).filter_by(email=email).first()
            if existing:
                if existing.role != role:
                    existing.role = role
            else:
                u = User(email=email, password_hash=hash_password("password123"))
                u.role = role
                db.add(u)
                created_users.append(u)
        db.commit()
        all_users = db.query(User).order_by(User.email).limit(users).all()
        print(f"users: {len(all_users)} total ({len(created_users)} new)")
        print("admin dashboard login: user000@example.com / password123")

        # --- website rows + jobs (only `enqueue` of them actually run) ---
        website_job_ids = []
        for i in range(websites):
            owner = all_users[i % len(all_users)]
            url = SAMPLE_URLS[i % len(SAMPLE_URLS)]
            site = Website(user_id=owner.id, url=url, domain=urlparse(url).netloc)
            db.add(site)
            db.flush()
            job = Job(user_id=owner.id, type=JobType.WEBSITE,
                      status=JobStatus.QUEUED, website_id=site.id)
            db.add(job)
            db.flush()
            if i < enqueue:
                website_job_ids.append(job.id)
        db.commit()

        for job_id in website_job_ids:
            tasks.enqueue_website(job_id)
        print(f"websites: {websites} rows/jobs created, {min(enqueue, websites)} enqueued")

        # --- sample files (real upload to local storage + enqueue) ---
        for i in range(files):
            owner = all_users[i % len(all_users)]
            content = (
                f"Demo document #{i}\n"
                "This is sample text uploaded by the seeder so the file pipeline "
                "has something to extract and analyze.\n"
                "Topics: distributed systems, background processing, AI analysis."
            ).encode()
            key = f"uploads/{owner.id}/seed-{i}.txt"
            storage.upload_bytes(key, content, "text/plain")
            f = File(user_id=owner.id, filename=f"seed-{i}.txt",
                     content_type="text/plain", size_bytes=len(content),
                     s3_key=key, status="uploaded")
            db.add(f)
            db.flush()
            job = Job(user_id=owner.id, type=JobType.FILE,
                      status=JobStatus.QUEUED, file_id=f.id)
            db.add(job)
            db.flush()
            db.commit()
            tasks.enqueue_file(job.id)
        print(f"files: {files} uploaded + enqueued")

        print("\nDone. Sample login:")
        print("  email:    user000@example.com")
        print("  password: password123")
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--users", type=int, default=100)
    p.add_argument("--websites", type=int, default=100)
    p.add_argument("--enqueue", type=int, default=3, help="website jobs to actually run (OpenAI cost)")
    p.add_argument("--files", type=int, default=2, help="sample files to upload + analyze")
    p.add_argument("--reset", action="store_true", help="clear demo data before seeding")
    args = p.parse_args()
    seed(args.users, args.websites, args.enqueue, args.files, args.reset)
