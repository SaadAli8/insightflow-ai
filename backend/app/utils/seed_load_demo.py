"""Load-demo seeder for the manager walkthrough.

This wrapper keeps the high-volume demo command separate from the everyday
seed script. It creates 100 users and 100 website jobs by default, then enqueues
all 100 jobs so the React dashboard, Flower, and Grafana show parallel work.

Run inside the api container:
    docker compose exec api python -m app.utils.seed_load_demo --reset
"""

import argparse

from app.utils.seed import seed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be 0 or greater")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a professional 100-user / 100-website load demo."
    )
    parser.add_argument("--users", type=positive_int, default=100)
    parser.add_argument("--websites", type=positive_int, default=100)
    parser.add_argument(
        "--enqueue",
        type=non_negative_int,
        default=100,
        help="website jobs to enqueue for processing",
    )
    parser.add_argument(
        "--files",
        type=non_negative_int,
        default=0,
        help="optional sample text files to upload and analyze",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="clear existing demo data before seeding",
    )
    args = parser.parse_args()

    if args.enqueue > args.websites:
        parser.error("--enqueue cannot be greater than --websites")

    seed(
        users=args.users,
        websites=args.websites,
        enqueue=args.enqueue,
        files=args.files,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
