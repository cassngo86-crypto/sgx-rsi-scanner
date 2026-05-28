import streamlit as st
import yfinance as yf
import pandas as pd

# Page setup
st.set_page_config(page_title="SGX Live Scanner", layout="wide")
st.title("🚀 Interactive SGX RSI & Income Scanner")

# 1. BASE CURATED WATCHLIST DEFAULTS
if "master_watchlist" not in st.session_state:
    st.session_state.master_watchlist = {
        'DBS': 'D05.SI',
        'YZJ': 'BS6.SI',
        'SATS': 'S58.SI',
        'UMS': '558.SI',
        'Frencken': 'E28.SI',
        'ST Engineering':'S63.SI',
        'Singtel':'Z74.SI',
        'China Aviation':'G92.SI',
        'Oiltek':'HQU.SI',
        'Sheng Siong':'OV8.SI',
        'AEM':'AWX.SI',
        'NTT DC Reit':'NTDU.SI',
        'Keppel DC Reit': 'AJBU.SI',
        'SIA Engineering':'S59.SI',
        'CSE Global':'544.SI'
    }

# --- 2. SIDEBAR FOR DYNAMIC USER ADDITIONS ---
st.sidebar.header("➕ Add Custom SGX Stock")
st.sidebar.markdown("Add any counter actively trading on the SGX market here:")
new_name = st.sidebar.text_input("Stock Short Name (e.g., UOB):").strip()
new_ticker = st.sidebar.text_input("SGX Ticker Code (e.g., U11.SI):").strip()

if st.sidebar.button("Add to Scanner Pool"):
    if new_name and new_ticker:
        ticker_formatted = new_ticker.upper()
        if not ticker_formatted.endswith(".SI") and "." not in ticker_formatted:
            ticker_formatted += ".SI"
            
        st.session_state.master_watchlist[new_name] = ticker_formatted
        st.sidebar.success(f"Added {new_name} ({ticker_formatted}) successfully!")
        st.rerun() 
    else:
        st.sidebar.error("Please fill out both name and ticker fields completely.")

# --- 3. DYNAMIC INTERACTIVE FILTER SELECTION ---
st.markdown("### 🔍 Filter and Customize Your Scan")
selected_names = st.multiselect(
    "Choose which stocks you want to display in your active monitor grid:",
    options=list(st.session_state.master_watchlist.keys()),
    default=list(st.session_state.master_watchlist.keys())
)

# --- 4. DATA ENGINE (WITH AUTOMATED DAILY CACHE INVALIDATION) ---
@st.cache_data(ttl=1800)
def get_stock_metrics(ticker, current_date):
    # 'current_date' is passed purely to force Streamlit to bust the cache every single day automatically.
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Fetch transactional pricing interval framework
        df = ticker_obj.history(period='3d', interval='5m')
        if df.empty:
            return None, 0.0
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        current_price = float(df['Close'].iloc[-1])
        
        # --- CALCULATE PURE YIELD FROM CASH FLOW RECORDS ---
        clean_yield = 0.0
        dividends_history = ticker_obj.dividends
        
        if not dividends_history.empty:
            # Look back exactly 365 days from the active current_date timestamp
            one_year_ago = pd.Timestamp(current_date, tz=dividends_history.index.tz) - pd.Timedelta(days=365)
            last_year_divs = dividends_history[dividends_history.index >= one_year_ago]
            total_cash_payout = float(last_year_divs.sum())
            
            if total_cash_payout > 0:
                if total_cash_payout > current_price:
                    total_cash_payout = total_cash_payout / 100.0
                
                clean_yield = (total_cash_payout / current_price) * 100.0
        
        if clean_yield > 15.0:
            clean_yield = clean_yield / 10.0 if (clean_yield / 10.0) <= 15.0 else clean_yield / 100.0
            
        # --- TECHNICAL INDICATOR (RSI) CALCULATIONS ---
        close = df['Close']
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=30).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=30).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df, clean_yield
    except:
        return None, 0.0


# --- 5. VISUAL MULTI-COLUMN CARD INTERFACE GRID ---
NUM_COLS = 4  

if not selected_names:
    st.info("💡 Select one or more tickers from the option bar above to run the signal analysis scan.")
else:
    active_batch = [(name, st.session_state.master_watchlist[name]) for name in selected_names]
    
    # Track today's date dynamically at the start of the layout loop
    today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
    
    for i in range(0, len(active_batch), NUM_COLS):
        row_slice = active_batch[i:i + NUM_COLS]
        cols = st.columns(NUM_COLS)
        
        for idx, (name, ticker) in enumerate(row_slice):
            with cols[idx]:
                with st.container(border=True):
                    # Pass the date string straight into your data engine function call
                    df, yield_value = get_stock_metrics(ticker, today_str)
                    
                    if df is not None:
                        current_price = float(df['Close'].iloc[-1])
                        current_rsi = float(df['RSI'].iloc[-1])
                        
                        # Display Metric KPI Card Info
                        st.metric(label=name, value=f"S${current_price:.3f}")
                        st.markdown(f"💰 **Div Yield:** `{yield_value:.2f}%`")
                        
                        # RSI Color Coding
                        if current_rsi < 35:
                            st.success(f"🟢 RSI: {current_rsi:.1f}")
                            st.caption("**OVER-SOLD / BUY ALERT**")
                        elif current_rsi > 70:
                            st.error(f"🔴 RSI: {current_rsi:.1f}")
                            st.caption("**OVER-BOUGHT / SELL ALERT**")
                        else:
                            st.info(f"🔵 RSI: {current_rsi:.1f}")
                    else:
                        st.warning(f"⚠️ {name} Offline")