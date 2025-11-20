import click
from app import create_app
from app.extensions import db
from app.services.data_price_service import fetch_price_from_yf, save_price_to_db
import json

@click.command()
@click.option('--daily_update', is_flag=True, help="Run daily price update")
def cli(daily_update):

    # 🟦如果是排程模式：只跑更新、不啟動 server
    if daily_update:
        app = create_app()
        with app.app_context():
            print("📌 自動更新每日股價…")

            # 讀取 TW500 清單
            with open("tw_top500.json", "r") as f:
                symbols = json.load(f)

            for symbol in symbols:
                print(f"📌 更新 {symbol} ...")
                df = fetch_price_from_yf(symbol, period="1d")

                if not df.empty:
                    save_price_to_db(symbol, df)

        print("🎉 今日更新完成！")
        return   # ← 不啟動 Flask，直接結束


    # 🟦如果沒有 daily_update → 正常啟動 Flask
    app = create_app()
    with app.app_context():
        db.create_all()

    app.run(debug=True)


if __name__ == "__main__":
    cli()
