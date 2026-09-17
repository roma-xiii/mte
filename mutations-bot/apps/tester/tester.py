from litestar import Litestar, get  
from litestar.openapi import OpenAPIConfig
import msgspec

from core import CandleList
from exchanges import klines_binance_fetch
from trading_controls import TradingControlPaper
from strategies import StrategyYojic

from stats import process_build_stats, print_results, plot_equity_curve


class BotConfig(msgspec.Struct):
    symbol: str = "SOLUSDT"
    interval: str = "5m"
    bars: int = 5760  
    # 1 - 46 - 2880 | 1.5 - 73 - 4320 | 2 - 220 - 5760 |3 - 492 - 8640
    balance_initial: float = 100.0
    risk_per_position_pct: float = 1.0
    leverage_max: float = 10.0
    risk_from_peak_balance: bool = True
    commission_rate: float = 0.00025

@get("/test-run")
async def test_run() -> dict[str, str]:
    bot_config = BotConfig()
    klines = klines_binance_fetch(
        symbol=bot_config.symbol,
        interval=bot_config.interval,
        total_bars=bot_config.bars,
    )

    candle_list = CandleList()
    trading_control = TradingControlPaper(
        candle_list=candle_list,
        balance_initial=100.0,
        risk_per_position_pct=1.0,
        leverage_max=10.0,
        risk_from_peak_balance=True,
        commission_rate=0.00025,
    )

    strategy = StrategyYojic(
        candle_list=candle_list,
        trading_control=trading_control,
    )

    strategy.start()

    for index, candle in enumerate(klines):
        if index > 2880:
            # continue
            pass

        strategy.candle_new(candle)

    strategy.stop_and_close()

    stats = process_build_stats(
        position_list=strategy.trading_control.position_list,
        balance_start=bot_config.balance_initial,
        balance_end=strategy.trading_control.balance,
        balance_peak=strategy.trading_control.balance_peak,
    )

    print_results(
        stats,
        bot_config.symbol,
        bot_config.interval,
        bot_config.bars,
        bot_config.risk_from_peak_balance,
    )
    plot_equity_curve(
        position_list=strategy.trading_control.position_list,
        title=f"Equity Curve — {bot_config.symbol} {bot_config.interval} ({bot_config.bars} bars)",
    )

    return {"status": "ok", "trades": strategy.trading_control.position_list}


app = Litestar(
    route_handlers=[test_run],
    openapi_config=OpenAPIConfig(title="Mutations Bot Tester", version="0.1.0"),
    debug=True,
)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "tester:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
