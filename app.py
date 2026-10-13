import math
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="TripFit | 내 지갑에 딱 맞는 여행", page_icon="✈️", layout="wide")

# 도시별 원화 기준 테스트 단가: 왕복 항공권 1인, 호텔 1실/1박,
# 식비·교통비·관광비 1인/1일. 실시간 가격이 아닙니다.
DATA_PATH = Path(__file__).resolve().parent / "travel_costs.csv"
REQUIRED = ["country", "city", "flight", "hotel", "food", "transport", "activity"]
STYLE_FACTORS = {"가성비형": 0.7, "일반형": 1.0, "럭셔리형": 1.6}
# 실측 계절 가격이 아닌 시연용 월별 계수입니다.
SEASON_FACTORS = {
    1: 1.05, 2: 1.00, 3: 1.00, 4: 1.05,
    5: 1.05, 6: 0.95, 7: 1.15, 8: 1.20,
    9: 0.95, 10: 1.05, 11: 0.95, 12: 1.15,
}
CATEGORIES = ["항공권", "숙박비", "식비", "교통비", "관광비"]

@st.cache_data
def load_costs(path: str):
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing_cols = set(REQUIRED) - set(df.columns)
    if missing_cols:
        raise ValueError(f"CSV 필수 열 누락: {sorted(missing_cols)}")
    for col in REQUIRED[2:]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    if df[REQUIRED[2:]].isna().any().any() or (df[REQUIRED[2:]] < 0).any().any():
        raise ValueError("CSV에 결측 또는 음수 비용이 있습니다.")
    if df.duplicated(["country", "city"]).any():
        raise ValueError("CSV에 국가-도시 중복 행이 있습니다.")
    return df


def calculate_travel_cost(cost, days, factor, activity_discount=0, *,
                          people=1, room_capacity=2, start_date=None,
                          adjustments=None):
    """그룹 전체 경비와 항목별 경비를 반환. 이전 함수의 기본 인자는 그대로 지원."""
    if adjustments is None:
        adjustments = {c: 1.0 for c in CATEGORIES}
    month_factor = SEASON_FACTORS[start_date.month] if start_date else 1.0
    rooms = math.ceil(people / room_capacity)
    values = {
        "항공권": round(float(cost["flight"]) * people * month_factor * adjustments["항공권"]),
        "숙박비": round(float(cost["hotel"]) * rooms * (days - 1) * factor * month_factor * adjustments["숙박비"]),
        "식비": round(float(cost["food"]) * people * days * factor * adjustments["식비"]),
        "교통비": round(float(cost["transport"]) * people * days * adjustments["교통비"]),
        "관광비": round(float(cost["activity"]) * people * days * factor *
                      (1 - activity_discount) * adjustments["관광비"]),
    }
    return values


def fmt(n):
    return f"{int(round(n)):,}원"


def find_cost(df, country, city):
    return df.loc[(df["country"] == country) & (df["city"] == city)].iloc[0]


def total_cost(cost, days, factor, **kwargs):
    return sum(calculate_travel_cost(cost, days, factor, **kwargs).values())



# --- CHARTS: editorial visual language ----------------------------------------
# 모든 차트는 흰 배경, 얇은 안내선, 무채색 + 제한된 포인트색으로 통일합니다.
CHART_INK = "#20252C"
CHART_MUTED = "#87929E"
CHART_BLUE = "#426A91"
CHART_LIGHT = "#CFD8E1"


def money_chart(data, label_col, value_col, *, height=300, highlight=None,
                target=None, sort="-x"):
    """금액 레이블이 붙은 편집형 가로 막대그래프."""
    chart_data = data[[label_col, value_col]].copy()
    chart_data[value_col] = pd.to_numeric(chart_data[value_col], errors="coerce").fillna(0)
    chart_data["금액표시"] = chart_data[value_col].map(fmt)
    chart_data["색상"] = chart_data[label_col].apply(
        lambda x: CHART_BLUE if highlight is None or str(x) == highlight else CHART_LIGHT
    )
    base = alt.Chart(chart_data).encode(
        y=alt.Y(f"{label_col}:N", sort=sort, title=None,
                axis=alt.Axis(labelFontSize=13, labelColor=CHART_INK,
                              labelPadding=13, ticks=False, domain=False)),
        x=alt.X(f"{value_col}:Q", title=None,
                axis=alt.Axis(labels=False, ticks=False, grid=False, domain=False)),
        tooltip=[alt.Tooltip(f"{label_col}:N", title="항목"),
                 alt.Tooltip(f"{value_col}:Q", title="예상 금액", format=",.0f")]
    )
    bars = base.mark_bar(size=22, cornerRadiusEnd=7).encode(
        color=alt.Color("색상:N", scale=None, legend=None)
    )
    labels = base.mark_text(align="left", baseline="middle", dx=9,
                            color=CHART_INK, fontSize=12, fontWeight=600).encode(
        text=alt.Text("금액표시:N")
    )
    layers = []
    if target is not None:
        layers.append(alt.Chart(pd.DataFrame({"기준": [target]})).mark_rule(
            color="#CF886F", strokeWidth=1.5, strokeDash=[4, 4]
        ).encode(x="기준:Q"))
    layers.extend([bars, labels])
    chart = alt.layer(*layers).properties(height=height, padding={"left": 0, "right": 100, "top": 10, "bottom": 10})
    st.altair_chart(chart.configure_view(stroke=None), use_container_width=True)


def grouped_comparison_chart(frame, label_col, first, second):
    """두 도시 항목별 비용 비교: 색을 두 가지로 제한."""
    melted = frame.melt(id_vars=[label_col], value_vars=[first, second],
                        var_name="여행지", value_name="원")
    melted["금액표시"] = melted["원"].map(fmt)
    chart = alt.Chart(melted).mark_bar(cornerRadiusEnd=4, size=11).encode(
        y=alt.Y(f"{label_col}:N", sort=CATEGORIES, title=None,
                axis=alt.Axis(labelFontSize=12, labelColor=CHART_INK, ticks=False, domain=False)),
        x=alt.X("원:Q", title=None, axis=alt.Axis(format="~s", grid=True,
              gridColor="#EDF0F3", tickCount=4, labelColor=CHART_MUTED, domain=False)),
        yOffset="여행지:N",
        color=alt.Color("여행지:N", scale=alt.Scale(domain=[first, second],
                        range=[CHART_BLUE, CHART_LIGHT]),
                        legend=alt.Legend(title=None, orient="top", labelFontSize=12)),
        tooltip=["여행지:N", f"{label_col}:N", alt.Tooltip("원:Q",format=",.0f")]
    ).properties(height=310)
    st.altair_chart(chart.configure_view(stroke=None), use_container_width=True)


# --- EDITORIAL TRAVEL LANDING -------------------------------------------------
# 레퍼런스의 큰 제목, 필터 칩, 풍경 사진 카드, 넉넉한 여백을 적용합니다.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');
:root { --ink: #141414; --muted: #686868; }
html, body, [class*="css"], .stApp {font-family: 'DM Sans','Noto Sans KR',sans-serif;}
.stApp {background: #fafafa; color: var(--ink);}
.block-container {max-width: 1190px; padding-top: 3.2rem; padding-bottom: 4rem;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"] {background: rgba(250,250,250,.90);}
h1,h2,h3 {letter-spacing:-.045em;}
.trip-brand {font-weight: 800; letter-spacing: -.05em; font-size: 1.15rem;}
.trip-kicker {font-weight:700; color:#888; text-transform:uppercase; font-size: .73rem; letter-spacing:.19em; margin-top:2.8rem; text-align:center;}
.trip-headline {font-size:clamp(2.7rem,5.3vw,4.6rem);font-weight:800;line-height:1.07;letter-spacing:-.065em;text-align:center;margin:1.1rem auto 1rem;}
.trip-subtitle {font-size:1rem;line-height:1.85;color:#747474;text-align:center;margin:0 auto 2.25rem;max-width:640px;}
.dest-card {height:320px;position:relative;border-radius:17px;overflow:hidden;background-size:cover;background-position:center;box-shadow:0 12px 25px rgba(0,0,0,.10); margin-bottom:.2rem;}
.dest-card::before {content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.12),transparent 25%,rgba(0,0,0,.75) 100%);}
.dest-tag {position:absolute;top:17px;left:15px;padding:7px 11px;border-radius:100px;background:rgba(255,255,255,.25);color:white;backdrop-filter:blur(9px);font-size:11px;font-weight:600;}
.dest-info {position:absolute;left:17px;right:14px;bottom:16px;color:white;}
.dest-title {font-size:21px;font-weight:750;letter-spacing:-.035em;line-height:1.25;margin-bottom:6px;}
.dest-desc {font-size:12px;line-height:1.5;color:rgba(255,255,255,.9);min-height:37px;}
.section-eyebrow {font-size:12px;font-weight:750;letter-spacing:.15em;color:#7b7b7b;margin: 2.4rem 0 .5rem;}
.section-heading {font-size:2rem;font-weight:800;letter-spacing:-.055em;margin:0 0 .6rem;}
.section-note {color:#777;font-size:.93rem;line-height:1.6;margin-bottom:1.5rem;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-radius:20px!important;}
[data-testid="stMetric"] {background:white;border:1px solid #ededed;padding:20px;border-radius:16px;}
[data-testid="stVegaLiteChart"] {background:#fff;border:1px solid #eeeeee;border-radius:18px;padding:18px 13px 6px;}
[data-testid="stMetricValue"] {font-weight:750;letter-spacing:-.04em;}
.stButton > button, [data-testid="stFormSubmitButton"] button {border-radius:12px!important; font-weight:700!important; min-height:43px;}
[data-testid="stFormSubmitButton"] button[kind="primary"] {background:#111!important;border-color:#111!important;color:white!important;}
[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {background:#333!important;border-color:#333!important;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:15px;}
[data-testid="stTabs"] button {font-weight:650;}
[data-testid="stRadio"] [role="radiogroup"] {gap:8px;}
@media(max-width: 700px) {.block-container {padding-top:1.8rem;} .trip-headline{font-size:2.5rem;} .dest-card{height:275px;}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="trip-brand">✈ TripFit <span style="font-weight:400;color:#aaa;font-size:12px">/ Travel, within reach.</span></div>',unsafe_allow_html=True)
st.markdown('<div class="trip-kicker">Explore · Plan · Go</div>',unsafe_allow_html=True)
st.markdown('<div class="trip-headline">Discover the World.</div>',unsafe_allow_html=True)
st.markdown('<div class="trip-subtitle">가고 싶은 곳을 발견하고, 나의 예산에 맞는 여행을 설계하세요.<br>여행지는 자유롭게. 예산은 스마트하게.</div>',unsafe_allow_html=True)

try:
    df = load_costs(str(DATA_PATH))
except (FileNotFoundError, ValueError, pd.errors.ParserError) as err:
    st.error(f"여행 비용 CSV를 불러올 수 없습니다: {err}")
    st.stop()

regions = {
    "전체": None,
    "아시아": {"일본","중국","대만","홍콩","태국","베트남","싱가포르","필리핀","인도네시아","말레이시아","인도"},
    "유럽": {"덴마크","프랑스","영국","이탈리아","스페인","독일","스위스","오스트리아","네덜란드","체코","헝가리","포르투갈","튀르키예"},
    "오세아니아": {"호주","뉴질랜드"},
    "아메리카": {"미국","캐나다","브라질"},
    "기타": {"아랍에미리트","이집트"},
}

# 이미지 URL은 화면 장식용이며 비용 정보와 무관합니다.
featured = [
    ("이탈리아", "베네치아", "Venice, Italy", "운하와 골목이 빚어내는 풍경", "https://images.unsplash.com/photo-1514890547357-a9ee288728e0?w=950&q=85"),
    ("일본", "도쿄", "Tokyo, Japan", "도시의 에너지와 골목의 낭만", "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=950&q=85"),
    ("필리핀", "세부", "Cebu, Philippines", "투명한 바다와 느긋한 휴식", "https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=950&q=85"),
    ("프랑스", "파리", "Paris, France", "산책만으로도 특별한 도시", "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=950&q=85"),
    ("덴마크", "코펜하겐", "Copenhagen, Denmark", "북유럽의 정갈한 일상과 풍경", "https://images.unsplash.com/photo-1513622470522-26c3c8a854bc?w=950&q=85"),
    ("이탈리아", "로마", "Rome, Italy", "오래된 건축과 찬란한 거리", "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=950&q=85"),
    ("인도네시아", "발리", "Bali, Indonesia", "자연 속에서 보내는 여유", "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=950&q=85"),
    ("호주", "시드니", "Sydney, Australia", "바다와 도시를 동시에 즐기는 여행", "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=950&q=85"),
    ("스위스", "인터라켄", "Interlaken, Switzerland", "알프스가 펼쳐지는 하루", "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=950&q=85"),
]
# CSV에 없는 도시는 탐색 이미지만 보여주고 선택 버튼은 제공하지 않습니다.
chosen_region = st.radio("지역 살펴보기", list(regions), horizontal=True, label_visibility="collapsed")
matching = [x for x in featured if (regions[chosen_region] is None or x[0] in regions[chosen_region])]
matching = matching[:4]
if not matching:
    st.info("해당 지역의 대표 사진은 준비 중이에요. 아래에서 국가와 도시를 직접 선택할 수 있어요.")
else:
    card_columns = st.columns(len(matching), gap="medium")
    for column, (c, v, en, desc, image_url) in zip(card_columns, matching):
        with column:
            card_html = (f'<div class="dest-card" style="background-image:url(\'{image_url}\')">'
                         f'<div class="dest-tag">Featured destination</div>'
                         f'<div class="dest-info"><div class="dest-title">{en}</div>'
                         f'<div class="dest-desc">{desc}</div></div></div>')
            st.markdown(card_html, unsafe_allow_html=True)
            if ((df["country"] == c) & (df["city"] == v)).any():
                def choose_destination(country=c, city=v):
                    st.session_state["chosen_country"] = country
                    st.session_state["chosen_city"] = city
                st.button("이 여행지로 계획하기 →", key=f"card_{c}_{v}",
                          use_container_width=True, on_click=choose_destination)
            else:
                st.caption("여행 영감 카드 · 경비 분석 대상 외")

st.markdown('<div class="section-eyebrow">YOUR JOURNEY</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">이제, 나만의 여행을 계획하세요.</div>', unsafe_allow_html=True)
st.markdown('<div class="section-note">여행 조건을 설정하고 분석 버튼을 누르면 결과가 표시됩니다. 아직 입력하지 않은 상태에서는 결과가 보이지 않아요.</div>', unsafe_allow_html=True)

countries = sorted(df["country"].unique().tolist())
if "chosen_country" not in st.session_state:
    st.session_state["chosen_country"] = None
if "chosen_city" not in st.session_state:
    st.session_state["chosen_city"] = None
if st.session_state["chosen_country"] not in countries:
    st.session_state["chosen_country"] = None

with st.container(border=True):
    row1, row2 = st.columns(2, gap="large")
    with row1:
        country_input = st.selectbox("여행 국가", countries, index=None,
                                     placeholder="어느 나라로 떠나고 싶으세요?", key="chosen_country")
    city_list = df.loc[df["country"] == country_input, "city"].tolist() if country_input else []
    if st.session_state["chosen_city"] not in city_list:
        st.session_state["chosen_city"] = None
    with row2:
        city_input = st.selectbox("여행 도시", city_list, index=None,
                                  placeholder="도시를 선택하세요", disabled=not city_list,
                                  key="chosen_city")
    with st.form("travel_inputs"):
        row3, row4, row5 = st.columns([1.15, 1, 1], gap="medium")
        with row3:
            budget_input = st.number_input("전체 여행 예산 (원)", min_value=0, value=1000000, step=100000)
        with row4:
            start_date_input = st.date_input("출발일", value=date.today(),
                                            min_value=date.today(), max_value=date.today()+timedelta(days=730))
        with row5:
            days_input = st.slider("여행 기간 (일)", min_value=2, max_value=14, value=4)
        row6, row7, row8 = st.columns(3, gap="medium")
        with row6:
            people_input = st.number_input("여행 인원", min_value=1, max_value=20, value=1, step=1)
        with row7:
            room_capacity_input = st.selectbox("객실당 인원 (가정)", [1, 2, 3, 4], index=1)
        with row8:
            style_input = st.selectbox("여행 스타일", list(STYLE_FACTORS), index=1)
        with st.expander("세부 지출 조정 · 선택 사항"):
            st.caption("기본값은 100%입니다. 항공·숙박·식비 등 원하는 항목을 조정할 수 있어요.")
            adjustment_inputs = {}
            for cat in CATEGORIES:
                adjustment_inputs[cat] = st.slider(cat, 50, 150, 100, 10, key=f"adj_{cat}")/100
        submitted = st.form_submit_button("여행 예산 분석하기   →", type="primary", use_container_width=True)

st.caption("인천 출발 · 원화 기준 · 실시간 가격이 아닌 예시 단가로 계산됩니다.")
if submitted:
    if not country_input or not city_input:
        st.error("여행 국가와 도시를 모두 선택한 다음 분석해 주세요.")
    else:
        st.session_state["tripfit_analysis"] = dict(
            country=country_input, city=city_input, budget=budget_input,
            start_date=start_date_input, days=days_input, people=people_input,
            room_capacity=room_capacity_input, style=style_input,
            adjustments=adjustment_inputs.copy()
        )

if "tripfit_analysis" not in st.session_state:
    st.info("여행 조건을 입력한 뒤 **여행 예산 분석하기**를 눌러 주세요.")
    st.stop()

# 마지막으로 분석 버튼을 누른 시점의 입력값으로 결과를 고정합니다.
inputs = st.session_state["tripfit_analysis"]
country = inputs["country"]
city = inputs["city"]
budget = inputs["budget"]
start_date = inputs["start_date"]
days = inputs["days"]
people = inputs["people"]
room_capacity = inputs["room_capacity"]
style = inputs["style"]
adjustments = inputs["adjustments"]

cost = find_cost(df, country, city)
factor = STYLE_FACTORS[style]
common = dict(people=people, room_capacity=room_capacity,
              start_date=start_date, adjustments=adjustments)
expenses = calculate_travel_cost(cost, days, factor, **common)
total = sum(expenses.values())
remaining = budget - total
expense_df = pd.DataFrame({"항목": list(expenses), "금액": list(expenses.values())})

st.divider()
st.subheader(f"🌏 {country} · {city} | {days}일 / {days-1}박 | {people}명 | {style}")
k1, k2, k3 = st.columns(3)
k1.metric("총 예상 경비", fmt(total))
k2.metric("설정한 총예산", fmt(budget))
k3.metric("남은 예산" if remaining >= 0 else "부족한 예산", fmt(abs(remaining)))
if remaining >= 0:
    st.success("설정한 예산 내에서 여행이 가능해요. (추정치 기준)")
else:
    st.warning("예산을 초과했어요. 아래 절약 전략 또는 여행지 추천을 확인해 보세요.")
if budget > 0:
    st.progress(min(total / budget, 1.0), text=f"예산 사용률 {total / budget:.1%}")
else:
    st.info("예산이 0원이어서 사용률을 표시하지 않습니다.")

analysis_tab, saving_tab, recommendation_tab, compare_tab, report_tab = st.tabs([
    "📊 예산 분석", "💡 절약 전략", "🌍 예산별 여행지 추천", "⚖️ 두 도시 비교", "📥 리포트 다운로드"
])

with analysis_tab:
    a, b = st.columns([2, 1])
    with a:
        st.subheader("항목별 예상 비용")
        money_chart(expense_df, "항목", "금액", height=285, highlight="항공권", sort=CATEGORIES)
    with b:
        st.subheader("상세 내역")
        st.dataframe(expense_df, hide_index=True, use_container_width=True)
        biggest = expense_df.loc[expense_df["금액"].idxmax()]
        if total > 0:
            st.info(f"최대 지출: {biggest['항목']} ({biggest['금액']/total:.1%})")
    st.caption(f"출발 월({start_date.month}월) 항공·숙박 가정 계수: {SEASON_FACTORS[start_date.month]:.2f}배. 도시별 실측 성수기가 아닌 공통 가정값입니다.")

with saving_tab:
    st.subheader("현재 계획 대비 절약 시나리오")
    candidates = []
    def add_scenario(name, alt_days, alt_factor, discount=0):
        alt = total_cost(cost, alt_days, alt_factor, activity_discount=discount, **common)
        if alt < total:
            candidates.append({"전략": name, "예상 경비": alt,
                               "절약 금액": total - alt, "예산 충족": alt <= budget})
    if days > 2:
        add_scenario("여행 하루 단축", days-1, factor)
    if factor > 0.7:
        add_scenario("가성비형으로 변경", days, 0.7)
    add_scenario("관광비 20% 절감", days, factor, 0.2)
    if days > 2 and factor > 0.7:
        add_scenario("가성비형 + 하루 단축", days-1, 0.7)
    scenario_df = pd.DataFrame(candidates)
    if scenario_df.empty:
        st.info("현재 조건에서 적용 가능한 절약 시나리오가 없어요.")
    else:
        # 기존 여행을 가장 적게 바꾸는 전략 우선: 관광비 → 스타일 → 일수 → 복합
        priority = {"관광비 20% 절감": 1, "가성비형으로 변경": 2,
                    "여행 하루 단축": 3, "가성비형 + 하루 단축": 4}
        scenario_df["변경 정도"] = scenario_df["전략"].map(priority)
        st.dataframe(scenario_df.drop(columns="변경 정도"), hide_index=True, use_container_width=True)
        affordable = scenario_df[scenario_df["예산 충족"]].sort_values(["변경 정도", "예상 경비"])
        if remaining < 0:
            if affordable.empty:
                st.warning("단일/복합 절약 시나리오만으로는 예산 충족이 어려워요. 다른 여행지도 검토해 보세요.")
            else:
                best = affordable.iloc[0]
                st.success(f"추천: {best['전략']} · 예상 경비 {fmt(best['예상 경비'])} · 절약 {fmt(best['절약 금액'])}")
        else:
            st.success("기본 계획이 이미 예산 범위에 들어와 있어요.")
        chart_df = pd.concat([pd.DataFrame([{"전략": "현재 계획", "예상 경비": total}]),
                              scenario_df[["전략", "예상 경비"]]], ignore_index=True)
        money_chart(chart_df.rename(columns={"전략":"여행 계획"}), "여행 계획", "예상 경비",
                    height=230, highlight="현재 계획", target=budget, sort=None)

with recommendation_tab:
    st.subheader("내 예산으로 갈 수 있는 여행지")
    st.caption("현재 입력한 날짜·인원·기간·스타일·지출 조정 비율을 모든 도시에도 동일하게 적용합니다.")
    recs = []
    for _, row in df.iterrows():
        estimate = total_cost(row, days, factor, **common)
        recs.append({"국가": row["country"], "도시": row["city"],
                     "예상 경비": estimate, "남는 예산": budget-estimate})
    recommendation_df = pd.DataFrame(recs)
    affordable_df = recommendation_df[recommendation_df["남는 예산"] >= 0].sort_values("예상 경비")
    st.metric("예산 내 여행 가능 도시", f"{len(affordable_df)} / {len(df)}곳")
    if affordable_df.empty:
        st.warning("이 조건에 맞는 도시가 없습니다. 기간, 예산 또는 여행 스타일을 조정해 보세요.")
    else:
        st.dataframe(affordable_df.head(20), hide_index=True, use_container_width=True)
        money_chart(affordable_df.head(8), "도시", "예상 경비", height=340, sort="x")
        st.caption("표는 경비가 낮은 순서로 최대 20곳, 차트는 10곳을 보여줍니다.")

with compare_tab:
    st.subheader("선택한 도시와 다른 도시 비교")
    options = [(r["country"], r["city"]) for _, r in df.iterrows()]
    labels = [f"{c} · {v}" for c, v in options]
    default_index = next((i for i, (c, v) in enumerate(options) if (c, v) != (country, city)), 0)
    other_label = st.selectbox("비교할 두 번째 도시", labels, index=default_index)
    other_index = labels.index(other_label)
    other_country, other_city = options[other_index]
    other_cost = find_cost(df, other_country, other_city)
    other_expenses = calculate_travel_cost(other_cost, days, factor, **common)
    comparison = pd.DataFrame({
        "항목": CATEGORIES,
        f"{country} · {city}": [expenses[c] for c in CATEGORIES],
        f"{other_country} · {other_city}": [other_expenses[c] for c in CATEGORIES],
    })
    grouped_comparison_chart(comparison, "항목", f"{country} · {city}", f"{other_country} · {other_city}")
    st.dataframe(comparison, hide_index=True, use_container_width=True)
    a_total, b_total = total, sum(other_expenses.values())
    st.info(f"총경비 비교: {country} {city} {fmt(a_total)} / {other_country} {other_city} {fmt(b_total)} · 차이 {fmt(abs(a_total-b_total))}")

with report_tab:
    st.subheader("나의 여행 경비표")
    st.write(f"여행지: {country} {city} | 출발일: {start_date} | {days}일 / {days-1}박")
    st.write(f"여행 인원: {people}명 | 객실당 {room_capacity}명 가정 | 스타일: {style}")
    st.write(f"설정 예산: {fmt(budget)} | 예상 경비: {fmt(total)}")
    download_df = expense_df.copy()
    download_df.insert(0, "국가", country)
    download_df.insert(1, "도시", city)
    download_df.insert(2, "출발일", str(start_date))
    download_df.insert(3, "여행 기간(일)", days)
    download_df.insert(4, "인원", people)
    download_df.insert(5, "스타일", style)
    st.download_button("📥 여행 예산 CSV 다운로드", data=download_df.to_csv(index=False).encode("utf-8-sig"),
                       file_name="tripfit_budget.csv", mime="text/csv")

st.divider()
st.caption("⚠️ 여행 경비는 예시 CSV 단가 및 가정된 월별 계수에 기반한 시뮬레이션 결과입니다. 실시간 항공권·호텔·환율·현지 시즌·예약 가능 여부를 반영하지 않습니다. 숙박비는 객실 1실 기준으로 가정합니다.")
