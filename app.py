import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="AI Candlestick Signal",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------- Pattern Detection ----------
def body(df):
    return abs(df['Close'] - df['Open'])

def upper_shadow(df):
    return df['High'] - df[['Open', 'Close']].max(axis=1)

def lower_shadow(df):
    return df[['Open', 'Close']].min(axis=1) - df['Low']

def is_bullish(df):
    return df['Close'] > df['Open']

def is_bearish(df):
    return df['Close'] < df['Open']

def detect_patterns(df):
    df = df.copy()
    n = len(df)
    signals = []
    if n < 5:
        return signals

    body_size = body(df)
    upper = upper_shadow(df)
    lower = lower_shadow(df)
    avg_body = body_size.rolling(10).mean().fillna(body_size.mean())

    # Hammer
    for i in range(2, n):
        if (lower.iloc[i] >= 2 * body_size.iloc[i] and
            upper.iloc[i] <= 0.3 * body_size.iloc[i] and
            body_size.iloc[i] > 0 and
            body_size.iloc[i] < avg_body.iloc[i] * 1.2 and
            df['Close'].iloc[i-2] > df['Close'].iloc[i]):
            signals.append({"index": i, "pattern": "Hammer", "type": "BUY",
                            "strength": "High", "reason": "Hammer in falling market → high chance of reversal upward"})

    # Shooting Star
    for i in range(2, n):
        if (upper.iloc[i] >= 2 * body_size.iloc[i] and
            lower.iloc[i] <= 0.3 * body_size.iloc[i] and
            body_size.iloc[i] > 0 and
            body_size.iloc[i] < avg_body.iloc[i] * 1.2 and
            df['Close'].iloc[i-2] < df['Close'].iloc[i]):
            signals.append({"index": i, "pattern": "Shooting Star", "type": "SELL",
                            "strength": "High", "reason": "Shooting Star in rising market → market can reverse downward"})

    # Three White Soldiers
    for i in range(2, n):
        if (is_bullish(df).iloc[i-2] and is_bullish(df).iloc[i-1] and is_bullish(df).iloc[i] and
            df['Close'].iloc[i] > df['Close'].iloc[i-1] > df['Close'].iloc[i-2] and
            body_size.iloc[i-2] > avg_body.iloc[i]*0.6 and
            body_size.iloc[i-1] > avg_body.iloc[i]*0.6 and
            body_size.iloc[i] > avg_body.iloc[i]*0.6):
            signals.append({"index": i, "pattern": "Three White Soldiers", "type": "BUY",
                            "strength": "Very High", "reason": "Three White Soldiers → strong uptrend starting"})

    # Three Black Crows
    for i in range(2, n):
        if (is_bearish(df).iloc[i-2] and is_bearish(df).iloc[i-1] and is_bearish(df).iloc[i] and
            df['Close'].iloc[i] < df['Close'].iloc[i-1] < df['Close'].iloc[i-2] and
            body_size.iloc[i-2] > avg_body.iloc[i]*0.6 and
            body_size.iloc[i-1] > avg_body.iloc[i]*0.6 and
            body_size.iloc[i] > avg_body.iloc[i]*0.6):
            signals.append({"index": i, "pattern": "Three Black Crows", "type": "SELL",
                            "strength": "Very High", "reason": "Three Black Crows → strong downtrend starting"})

    # Green Marubozu
    for i in range(1, n):
        if (is_bullish(df).iloc[i] and
            upper.iloc[i] < 0.1 * body_size.iloc[i] and
            lower.iloc[i] < 0.1 * body_size.iloc[i] and
            body_size.iloc[i] > avg_body.iloc[i] * 1.5):
            signals.append({"index": i, "pattern": "Green Marubozu", "type": "BUY",
                            "strength": "High", "reason": "Big green candle with almost no shadows → strong buying"})

    # Red Marubozu
    for i in range(1, n):
        if (is_bearish(df).iloc[i] and
            upper.iloc[i] < 0.1 * body_size.iloc[i] and
            lower.iloc[i] < 0.1 * body_size.iloc[i] and
            body_size.iloc[i] > avg_body.iloc[i] * 1.5):
            signals.append({"index": i, "pattern": "Red Marubozu", "type": "SELL",
                            "strength": "High", "reason": "Big red candle with almost no shadows → strong selling"})

    # Bullish Engulfing
    for i in range(1, n):
        if (is_bearish(df).iloc[i-1] and is_bullish(df).iloc[i] and
            df['Open'].iloc[i] < df['Close'].iloc[i-1] and
            df['Close'].iloc[i] > df['Open'].iloc[i-1]):
            signals.append({"index": i, "pattern": "Bullish Engulfing", "type": "BUY",
                            "strength": "High", "reason": "Green candle engulfs previous red → bullish reversal"})

    # Bearish Engulfing
    for i in range(1, n):
        if (is_bullish(df).iloc[i-1] and is_bearish(df).iloc[i] and
            df['Open'].iloc[i] > df['Close'].iloc[i-1] and
            df['Close'].iloc[i] < df['Open'].iloc[i-1]):
            signals.append({"index": i, "pattern": "Bearish Engulfing", "type": "SELL",
                            "strength": "High", "reason": "Red candle engulfs previous green → bearish reversal"})

    return signals

def get_final_signal(signals, df):
    if not signals:
        return "HOLD", "No strong pattern detected.", 0
    recent = [s for s in signals if s["index"] >= len(df) - 6]
    if not recent:
        recent = signals[-3:]
    buy_score = sum(2 if s["strength"] == "Very High" else 1 for s in recent if s["type"] == "BUY")
    sell_score = sum(2 if s["strength"] == "Very High" else 1 for s in recent if s["type"] == "SELL")
    if buy_score > sell_score + 1:
        return "BUY", recent[-1]["reason"], buy_score
    elif sell_score > buy_score + 1:
        return "SELL", recent[-1]["reason"], sell_score
    else:
        return "HOLD", "Mixed signals. Wait for clearer pattern.", max(buy_score, sell_score)

# ---------- UI ----------
st.title("📈 AI Candlestick Signal")
st.caption("Based on Bald Trader patterns • Works on Mobile")

symbol = st.text_input("Enter Symbol", value="RELIANCE.NS",
                       placeholder="RELIANCE.NS / TCS.NS / BTC-USD")

col1, col2 = st.columns(2)
with col1:
    period = st.selectbox("Period", ["5d", "1mo", "3mo"], index=1)
with col2:
    interval = st.selectbox("Interval", ["15m", "1h", "1d"], index=2)

if st.button("Get Signal", type="primary", use_container_width=True):
    with st.spinner("Scanning..."):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval)
            if df.empty or len(df) < 10:
                st.error("Not enough data. Try another symbol.")
            else:
                df = df.reset_index()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                df = df.rename(columns=str.title)

                signals = detect_patterns(df)
                final, reason, score = get_final_signal(signals, df)

                if final == "BUY":
                    st.success(f"### 🟢 BUY")
                elif final == "SELL":
                    st.error(f"### 🔴 SELL")
                else:
                    st.warning(f"### 🟡 HOLD")

                st.write(reason)
                st.caption(f"Score: {score}")

                # Chart
                fig = go.Figure(data=[go.Candlestick(
                    x=df['Datetime'] if 'Datetime' in df.columns else df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close']
                )])
                fig.update_layout(
                    height=400,
                    margin=dict(l=10, r=10, t=30, b=10),
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark"
                )
                st.plotly_chart(fig, use_container_width=True)

                if signals:
                    st.subheader("Recent Patterns")
                    recent = sorted(signals, key=lambda x: x["index"], reverse=True)[:6]
                    for s in recent:
                        st.write(f"**{s['pattern']}** → {s['type']} ({s['strength']})")

        except Exception as e:
            st.error(f"Error: {e}")
            st.info("Try: RELIANCE.NS, TCS.NS, HDFCBANK.NS, BTC-USD")

st.markdown("---")
st.caption("Educational only • Not financial advice")
