# run.py

import click
from app import create_app
from app.extensions import db

@click.command()
@click.option("--daily_update", is_flag=True, help="Run daily price update task")
def cli(daily_update):

    # ========================
    # 📌 Daily Update Mode
    # ========================
    if daily_update:
        app = create_app()
        with app.app_context():
            print("📌 Daily auto-update is not yet implemented for FinMind.")
            print("👉 But run.py is ready for future task scheduling.")
        return

    # ========================
    # 📌 Normal Flask Mode
    # ========================
    app = create_app()
    with app.app_context():
        db.create_all()

    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    cli()
