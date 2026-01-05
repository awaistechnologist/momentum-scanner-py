"""Streamlit UI for interactive scanning."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import logging

from scanner.config import Config
from scanner.config.universes import UNIVERSE_LISTS
from scanner.core.scanner import Scanner
from scanner.core.indicators import bars_to_df
from scanner.integrations.export import Exporter
from scanner.integrations.telegram import TelegramBot

logger = logging.getLogger(__name__)


# Page config
st.set_page_config(
    page_title="Momentum Scanner",
    page_icon="📈",
    layout="wide"
)


def create_chart(symbol, bars):
    """Create candlestick chart with indicators."""
    df = bars_to_df(bars)

    if df.empty:
        return None

    # Calculate indicators for display
    from scanner.core.indicators import (
        calculate_ema, calculate_sma, calculate_rsi, calculate_macd, calculate_volume_average
    )

    close = df["close"]
    df["ema_9"] = calculate_ema(close, 9)
    df["ema_21"] = calculate_ema(close, 21)
    df["sma_50"] = calculate_sma(close, 50)
    df["rsi"] = calculate_rsi(close, 14)
    macd, signal, hist = calculate_macd(close)
    df["macd"] = macd
    df["macd_signal"] = signal
    df["macd_hist"] = hist
    df["volume_avg"] = calculate_volume_average(df["volume"], 20)

    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=(f"{symbol} - Price & EMAs", "RSI", "MACD", "Volume")
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price"
        ),
        row=1, col=1
    )

    # EMAs
    fig.add_trace(go.Scatter(x=df.index, y=df["ema_9"], name="EMA 9", line=dict(color="blue", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["ema_21"], name="EMA 21", line=dict(color="orange", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["sma_50"], name="SMA 50", line=dict(color="purple", width=1)), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI", line=dict(color="green")), row=2, col=1)
    fig.add_hline(y=50, line_dash="dash", line_color="gray", row=2, col=1)
    fig.add_hline(y=65, line_dash="dash", line_color="red", row=2, col=1)

    # MACD
    fig.add_trace(go.Scatter(x=df.index, y=df["macd"], name="MACD", line=dict(color="blue")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], name="Signal", line=dict(color="red")), row=3, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Histogram"), row=3, col=1)

    # Volume
    fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="Volume"), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["volume_avg"], name="Vol Avg", line=dict(color="red")), row=4, col=1)

    fig.update_layout(
        height=900,
        showlegend=True,
        xaxis_rangeslider_visible=False
    )

    return fig


def main():
    """Main Streamlit app."""
    st.title("📈 Short-Term Momentum Scanner")

    # Show helpful info banner
    st.info("ℹ️ **Quick Start:** Default configuration scans 96 US stocks using Alpaca API with actionable filter enabled. Adjust settings in sidebar or use config.json.")

    # Sidebar - Configuration
    st.sidebar.header("⚙️ Configuration")

    # Config file
    config_file = st.sidebar.text_input(
        "Config File (optional)",
        value="config.json",
        placeholder="config.json",
        help="Leave as 'config.json' to use default config"
    )

    # Load config
    if config_file:
        try:
            config = Config.from_file(config_file)
            st.sidebar.success(f"✅ Config loaded from {config_file}")
        except Exception as e:
            st.sidebar.error(f"❌ Config error: {e}")
            config = Config.from_defaults()
    else:
        config = Config.from_defaults()

    # Universe selection
    st.sidebar.subheader("🌍 Universe")

    # Get default universe from config or use US lists
    default_universe = config.get("universe.lists", [])
    if not default_universe:
        default_universe = ["US_LIQUID_TECH", "US_BLUE_CHIP", "US_GROWTH", "US_FINANCIAL", "US_HEALTHCARE"]

    selected_lists = st.sidebar.multiselect(
        "Pre-defined Lists",
        options=list(UNIVERSE_LISTS.keys()),
        default=default_universe,
        help="Default: All US lists (96 stocks total)"
    )

    custom_symbols_input = st.sidebar.text_area(
        "Custom Symbols (comma-separated)",
        placeholder="AAPL, MSFT, GOOGL"
    )

    custom_symbols = []
    if custom_symbols_input:
        custom_symbols = [s.strip().upper() for s in custom_symbols_input.split(",")]

    # Strategy parameters
    st.sidebar.subheader("📊 Strategy Parameters")

    rsi_min = st.sidebar.slider("RSI Min", 0, 100, config.get("strategy.rsi_min", 50))
    rsi_max = st.sidebar.slider("RSI Max", 0, 100, config.get("strategy.rsi_max", 65))
    score_threshold = st.sidebar.slider("Score Threshold", 0, 100, config.get("strategy.score_threshold", 60))
    top_n = st.sidebar.number_input("Top N Results", min_value=1, max_value=50, value=config.get("strategy.top_n", 15))

    # Actionable filter parameters
    st.sidebar.subheader("✅ Actionable Filter")

    actionable_enabled = st.sidebar.checkbox(
        "Enable Actionable Filter",
        value=config.get("actionable.enabled", True),
        help="Apply stricter filters and calculate position sizing"
    )

    if actionable_enabled:
        account_size = st.sidebar.number_input(
            "Account Size ($)",
            min_value=1000,
            max_value=1000000,
            value=config.get("actionable.risk.account_size", 10000),
            step=1000
        )

        risk_pct = st.sidebar.slider(
            "Risk % Per Trade",
            0.1, 5.0,
            config.get("actionable.risk.risk_percent_per_trade", 1.0),
            0.1
        )

        min_rr = st.sidebar.slider(
            "Min R/R Ratio",
            1.0, 5.0,
            config.get("actionable.technical.min_rr", 2.0),
            0.1
        )

        min_vol_ratio = st.sidebar.slider(
            "Min Volume Ratio",
            0.5, 3.0,
            config.get("actionable.technical.min_volume_ratio", 1.2),
            0.1
        )

        require_rsi_non_neg = st.sidebar.checkbox(
            "Require RSI Rising/Flat (no ↓)",
            value=config.get("actionable.technical.require_rsi_slope_non_negative", True)
        )

        # Update config with actionable values
        if "actionable" not in config._data:
            config._data["actionable"] = {}
        config._data["actionable"]["enabled"] = True
        config._data["actionable"]["risk"] = {
            "account_size": account_size,
            "risk_percent_per_trade": risk_pct
        }
        config._data["actionable"]["technical"] = {
            "min_rr": min_rr,
            "min_volume_ratio": min_vol_ratio,
            "require_rsi_slope_non_negative": require_rsi_non_neg,
            "allow_volume_rising_days": 3,
            "earnings_lookahead_trading_days": 7,
            "atr_min": 1.0,
            "gapdown_guard_pct": -1.5,
            "must_hold_trend": True
        }
        config._data["actionable"]["liquidity"] = {
            "min_price": 5.0,
            "min_avg_dollar_volume_20d": 10000000
        }
    else:
        if "actionable" in config._data:
            config._data["actionable"]["enabled"] = False

    # Update config with UI values
    config._data["strategy"]["rsi_min"] = rsi_min
    config._data["strategy"]["rsi_max"] = rsi_max
    config._data["strategy"]["score_threshold"] = score_threshold
    config._data["strategy"]["top_n"] = top_n

    # Data provider
    provider_options = ["alpaca", "alphavantage", "finnhub", "twelvedata"]
    current_provider = config.get("data.provider", "alpaca")

    # Find index of current provider
    try:
        default_idx = provider_options.index(current_provider)
    except ValueError:
        default_idx = 0  # Default to alpaca

    provider = st.sidebar.selectbox(
        "Data Provider",
        provider_options,
        index=default_idx,
        help="Alpaca recommended for US stocks (batch API)"
    )
    config._data["data"]["provider"] = provider

    # Scan button
    if st.sidebar.button("🔍 Run Scan", type="primary"):
        from scanner.config.universes import get_universe
        symbols = get_universe(selected_lists, custom_symbols)

        if not symbols:
            st.error("❌ No symbols selected. Please choose a universe or enter custom symbols.")
        else:
            with st.spinner(f"Scanning {len(symbols)} symbols..."):
                try:
                    scanner = Scanner(config)
                    result = scanner.scan(symbols=symbols, max_workers=5)

                    # Store in session state
                    st.session_state["scan_result"] = result
                    st.success(f"✅ Scan complete! Found {len(result.signals)} signals from {result.scanned_count} symbols.")
                except Exception as e:
                    st.error(f"❌ Scan failed: {e}")
                    logger.error(f"Scan error: {e}", exc_info=True)

    # Display results
    if "scan_result" in st.session_state:
        result = st.session_state["scan_result"]

        # Determine display mode
        show_actionable = result.actionable_signals is not None and result.actionable_count and result.actionable_count > 0

        # Readiness banner (if enabled)
        readiness_status = getattr(result, 'readiness_status', None)
        readiness_message = getattr(result, 'readiness_message', None)
        readiness_can_run = getattr(result, 'readiness_can_run', None)

        if readiness_status:
            # Color-coded banner based on status
            if readiness_status == "READY":
                st.success(f"✅ **READY** — {readiness_message}")
            elif readiness_status == "EARLY":
                st.warning(f"⏰ **EARLY** — {readiness_message}")
            elif readiness_status == "RE_RUN":
                st.warning(f"🔄 **RE-RUN** — {readiness_message}")
            elif readiness_status == "STALE":
                st.error(f"⚠️ **STALE** — {readiness_message}")
            elif readiness_status == "HOLIDAY":
                st.error(f"🚫 **MARKET CLOSED** — {readiness_message}")

            # Market open guidance (below readiness banner)
            market_open_guidance = getattr(result, 'market_open_guidance', None)
            if market_open_guidance:
                st.info(market_open_guidance)

        # Provenance header (Tweak #3) - with fallback for backward compatibility
        mode = getattr(result, 'mode', None)
        regime = getattr(result, 'regime', None)
        data_provider = getattr(result, 'data_provider', None)
        timeframe = getattr(result, 'timeframe', None)
        last_bar_timestamp = getattr(result, 'last_bar_timestamp', None)

        st.info(
            f"**Mode:** {mode.upper() if mode else 'MOMENTUM'} "
            f"{'| **Regime:** ' + regime if regime else ''} "
            f"| **Provider:** {data_provider.upper() if data_provider else 'UNKNOWN'} "
            f"| **Timeframe:** {timeframe if timeframe else '1d'} "
            f"{'| **Last Bar:** ' + last_bar_timestamp.strftime('%Y-%m-%d %H:%M') if last_bar_timestamp else ''}"
        )

        # Summary stats
        if show_actionable:
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Symbols Scanned", result.scanned_count)
            with col2:
                st.metric("Signals Found", result.passed_count)
            with col3:
                st.metric("✅ Actionable", result.actionable_count)
            with col4:
                avg_rr = sum(a.signal.risk_reward for a in result.actionable_signals if a.signal.risk_reward) / max(len(result.actionable_signals), 1)
                st.metric("Avg R/R", f"{avg_rr:.1f}")
            with col5:
                total_risk = sum(a.risk_dollars for a in result.actionable_signals)
                st.metric("Total Risk", f"${total_risk:.0f}")
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Symbols Scanned", result.scanned_count)
            with col2:
                st.metric("Signals Found", result.passed_count)
            with col3:
                avg_score = sum(s.score for s in result.signals) / len(result.signals) if result.signals else 0
                st.metric("Avg Score", f"{avg_score:.1f}")
            with col4:
                st.metric("Scan Time", result.scan_timestamp.strftime("%Y-%m-%d %H:%M"))

        # Results table
        if show_actionable and result.actionable_signals:
            # Actionable signals tab
            tab1, tab2 = st.tabs(["✅ Actionable Trades", "❌ Rejected"])

            with tab1:
                st.subheader(f"📋 Actionable Trades ({result.actionable_count})")

                # Convert to DataFrame with sizing
                data = []
                for i, actionable in enumerate(result.actionable_signals, 1):
                    signal = actionable.signal
                    rsi_display = f"{signal.rsi:.0f}{signal.rsi_slope}" if signal.rsi and signal.rsi_slope else "-"
                    data.append({
                        "#": i,
                        "Symbol": signal.symbol,
                        "Price": f"${signal.price:.2f}",
                        "Score": f"{signal.score:.0f}",
                        "RSI": rsi_display,
                        "Entry": f"${signal.suggested_entry:.2f}" if signal.suggested_entry else "-",
                        "Stop": f"${signal.suggested_stop:.2f}" if signal.suggested_stop else "-",
                        "Target": f"${signal.suggested_target:.2f}" if signal.suggested_target else "-",
                        "R/R": f"{signal.risk_reward:.1f}" if signal.risk_reward else "-",
                        "Size": actionable.position_size_shares,
                        "Risk $": f"${actionable.risk_dollars:.0f}",
                        "Reward $": f"${actionable.reward_dollars:.0f}",
                        "Notes": ", ".join(actionable.notes[:2])
                    })

                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)

            with tab2:
                st.subheader(f"❌ Rejected Signals ({len(result.rejected_signals) if result.rejected_signals else 0})")

                if result.rejected_signals:
                    rej_data = []
                    for rejected in result.rejected_signals:
                        rej_data.append({
                            "Symbol": rejected.symbol,
                            "Rejection Reasons": ", ".join(rejected.rejection_reasons)
                        })
                    rej_df = pd.DataFrame(rej_data)
                    st.dataframe(rej_df, use_container_width=True)
                else:
                    st.info("No signals were rejected")

        elif result.signals:
            st.subheader("📋 Signals")

            # Standard signals (no actionable filter)
            data = []
            for i, signal in enumerate(result.signals, 1):
                rsi_display = f"{signal.rsi:.0f}{signal.rsi_slope}" if signal.rsi and signal.rsi_slope else (f"{signal.rsi:.1f}" if signal.rsi else "-")
                data.append({
                    "#": i,
                    "Symbol": signal.symbol,
                    "Price": f"${signal.price:.2f}",
                    "Score": f"{signal.score:.1f}",
                    "RSI": rsi_display,
                    "Entry": f"${signal.suggested_entry:.2f}" if signal.suggested_entry else "-",
                    "Stop": f"${signal.suggested_stop:.2f}" if signal.suggested_stop else "-",
                    "Target": f"${signal.suggested_target:.2f}" if signal.suggested_target else "-",
                    "R/R": f"{signal.risk_reward:.1f}" if signal.risk_reward else "-",
                    "Signals": ", ".join(signal.signals_hit[:2])
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)

        # Signal detail view (only if we have signals)
        if result.signals:
            st.subheader("🔍 Signal Details")

            selected_signal_idx = st.selectbox(
                "Select Signal to View",
                range(len(result.signals)),
                format_func=lambda i: f"{i+1}. {result.signals[i].symbol} (Score: {result.signals[i].score:.1f})"
            )

            selected_signal = result.signals[selected_signal_idx]

            # Display signal info
            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown(f"### {selected_signal.symbol}")
                st.metric("Price", f"${selected_signal.price:.2f}")
                st.metric("Score", f"{selected_signal.score:.1f}")

                st.markdown("**Signals Hit:**")
                for sig in selected_signal.signals_hit:
                    st.markdown(f"- {sig}")

                if selected_signal.suggested_entry:
                    st.markdown("**Trade Setup:**")
                    st.markdown(f"- Entry: ${selected_signal.suggested_entry:.2f}")
                    st.markdown(f"- Stop: ${selected_signal.suggested_stop:.2f}")
                    st.markdown(f"- Target: ${selected_signal.suggested_target:.2f}")
                    st.markdown(f"- R/R: {selected_signal.risk_reward:.1f}")

            with col2:
                # Get bars for charting
                try:
                    scanner = Scanner(config)
                    _, bars, _ = scanner._get_data_for_symbol(selected_signal.symbol)
                    if bars:
                        chart = create_chart(selected_signal.symbol, bars)
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                except Exception as e:
                    st.error(f"Failed to load chart: {e}")

            # Export options
            st.subheader("💾 Export")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📄 Export CSV"):
                    csv_file = f"./output/scan_{result.scan_timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
                    Exporter.export_to_csv(result.signals, csv_file)
                    st.success(f"Exported to {csv_file}")

            with col2:
                if st.button("📋 Export JSON"):
                    json_file = f"./output/scan_{result.scan_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                    Exporter.export_to_json(result, json_file)
                    st.success(f"Exported to {json_file}")

            with col3:
                if st.button("📱 Send to Telegram"):
                    bot_token = config.get("notifications.telegram.bot_token")
                    chat_id = config.get("notifications.telegram.chat_id")
                    if bot_token and chat_id:
                        try:
                            bot = TelegramBot(bot_token, chat_id)
                            success = bot.send_simple_summary(result.signals, "UI Scan Results")
                            if success:
                                st.success("Sent to Telegram!")
                            else:
                                st.error("Failed to send to Telegram (check logs/credentials)")
                        except Exception as e:
                            st.error(f"Failed to send: {e}")
                    else:
                        st.warning("Telegram credentials not configured")
        else:
            st.info("No signals found. Try adjusting the strategy parameters.")


if __name__ == "__main__":
    main()
