import matplotlib.pyplot as plt
from typing import List

from core import PointPosition


def calculate_trade_stats(trades: List[PointPosition]):
    if not trades:
        return {
            'total_trades': 0,
            'total_pnl': 0.0,
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'max_win': 0.0,
            'max_loss': 0.0
        }

    total_trades = len(trades)
    wins = 0
    total_pnl = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins_list = []
    losses_list = []

    for trade in trades:
        pnl = trade.profit if trade.profit is not None else 0.0
        total_pnl += pnl
        if pnl > 0:
            wins += 1
            gross_profit += pnl
            wins_list.append(pnl)
        else:
            gross_loss += abs(pnl)
            losses_list.append(pnl)

    winrate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    avg_win = sum(wins_list) / len(wins_list) if wins_list else 0.0
    avg_loss = sum(losses_list) / len(losses_list) if losses_list else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf') if gross_profit > 0 else 0.0

    return {
        'total_trades': total_trades,
        'total_pnl': round(total_pnl, 2),
        'winrate': round(winrate, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else '∞',
        'max_win': round(max(wins_list), 2) if wins_list else 0.0,
        'max_loss': round(min(losses_list), 2) if losses_list else 0.0
    }

def process_build_stats(
    position_list: List[PointPosition],
    balance_start: float,
    balance_end: float,
    balance_peak: float,
):
    stats = calculate_trade_stats(position_list)
    stats['start_balance'] = round(balance_start, 2)
    stats['end_balance'] = round(balance_end, 2)
    if balance_start != 0:
        stats['net_return_pct'] = round((balance_end - balance_start) / balance_start * 100, 2)
    else:
        stats['net_return_pct'] = 0.0
    stats['peak_equity'] = round(balance_peak, 2)

    return stats

def plot_equity_curve(position_list: List[PointPosition], title="Equity Curve (Balance after Fees)"):
    if not position_list:
        print("Нет сделок — equity curve пустая")
        return

    closed_points = [
        trade
        for trade in position_list
        if trade.exit_time is not None and trade.balance_after is not None
    ]
    if not closed_points:
        print("Нет закрытых сделок с equity данными — график пустой")
        return

    dates = [trade.exit_time for trade in closed_points]
    equities = [trade.balance_after for trade in closed_points]

    plt.figure(figsize=(14, 7))
    plt.plot(dates, equities, color='blue', linewidth=2, label='Equity Balance')
    plt.fill_between(dates, equities, color='blue', alpha=0.1)

    plt.title(title)
    plt.xlabel('Время')
    plt.ylabel('Баланс (USDT)')
    # Без этого matplotlib часто показывает подписи 0.0, 0.2, 0.4… при реальном уровне ~100
    # (смещение "+1e2" / offset в углу оси — легко не заметить).
    plt.gca().ticklabel_format(axis='y', useOffset=False, style='plain')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

def print_results(
    stats: dict,
    symbol: str,
    interval: str,
    bars_lenght: int,
    risk_from_peak_balance: bool,
):
    print("\n" + "="*60)
    print("BACKTEST RESULTS (Market Structure + 0.5 Fib Pullback)")
    print("="*60)
    print(f"Символ:          {symbol}")
    print(f"Таймфрейм:       {interval}")   # исправлено
    print(f"Всего баров:     {bars_lenght}")
    print(f"Риск от пика:    {'да' if risk_from_peak_balance else 'нет'}")
    print(f"Пиковый equity:  {stats['peak_equity']:.2f} USDT")
    print(f"Стартовый баланс:{stats['start_balance']:.2f} USDT")
    print(f"Финальный баланс:{stats['end_balance']:.2f} USDT")
    print(f"Доходность:      {stats['net_return_pct']:+.2f}%")
    print(f"Всего трейдов:   {stats['total_trades']}")
    print(f"Общий PnL:       {stats['total_pnl']:+.2f} USDT")
    print(f"Winrate:         {stats['winrate']}%")
    print(f"Avg Win:         {stats['avg_win']:+.2f}")
    print(f"Avg Loss:        {stats['avg_loss']:+.2f}")
    print(f"Profit Factor:   {stats['profit_factor']}")
    print(f"Max Win:         {stats['max_win']:+.2f}")
    print(f"Max Loss:        {stats['max_loss']:+.2f}")
    print("="*60)
