
import streamlit as st
import pandas as pd


# 여행 조건에 따른 총경비 계산 함수
def calculate_travel_cost(cost, days, factor, activity_discount=0):

    flight = int(cost["flight"])

    hotel = round(
        int(cost["hotel"]) * factor * (days - 1)
    )

    food = round(
        int(cost["food"]) * factor * days
    )

    transport = int(cost["transport"]) * days

    activity = round(
        int(cost["activity"]) * factor * days
        * (1 - activity_discount)
    )

    total = flight + hotel + food + transport + activity

    return total


# 웹사이트 기본 설정
st.set_page_config(
    page_title="TripFit",
    page_icon="✈️",
    layout="centered"
)

# 웹사이트 제목
st.title("✈️ TripFit")
st.subheader("내 지갑에 딱 맞는 여행")

# 웹사이트 소개
st.write("내 예산으로 원하는 여행을 떠날 수 있을까요?")
st.write("여행 조건을 입력하고 예상 경비를 확인해 보세요!")


# 국가별 여행 도시 목록
travel_destinations = {
    # 아시아
    "일본": ["도쿄", "오사카", "후쿠오카", "삿포로", "오키나와"],
    "중국": ["베이징", "상하이", "칭다오", "청두"],
    "대만": ["타이베이", "가오슝", "타이중"],
    "홍콩": ["홍콩"],
    "태국": ["방콕", "치앙마이", "푸켓", "파타야"],
    "베트남": ["다낭", "하노이", "호찌민", "나트랑", "푸꾸옥"],
    "싱가포르": ["싱가포르"],
    "필리핀": ["세부", "마닐라", "보라카이"],
    "인도네시아": ["발리", "자카르타", "족자카르타"],
    "말레이시아": ["쿠알라룸푸르", "코타키나발루", "페낭"],
    "인도": ["뉴델리", "뭄바이", "자이푸르"],

    # 유럽
    "덴마크": ["코펜하겐", "오르후스", "오덴세", "올보르"],
    "프랑스": ["파리", "니스", "리옹"],
    "영국": ["런던", "맨체스터", "에든버러"],
    "이탈리아": ["로마", "밀라노", "피렌체", "베네치아"],
    "스페인": ["바르셀로나", "마드리드", "세비야"],
    "독일": ["베를린", "뮌헨", "프랑크푸르트"],
    "스위스": ["취리히", "인터라켄", "루체른"],
    "오스트리아": ["빈", "잘츠부르크", "인스브루크"],
    "네덜란드": ["암스테르담", "로테르담"],
    "체코": ["프라하", "체스키크룸로프"],
    "헝가리": ["부다페스트"],
    "포르투갈": ["리스본", "포르투"],
    "튀르키예": ["이스탄불", "카파도키아", "안탈리아"],

    # 북미
    "미국": ["뉴욕", "로스앤젤레스", "샌프란시스코", "라스베이거스", "하와이"],
    "캐나다": ["밴쿠버", "토론토", "몬트리올"],

    # 남미
    "브라질": ["리우데자네이루", "상파울루"],

    # 오세아니아
    "호주": ["시드니", "멜버른", "브리즈번", "퍼스"],
    "뉴질랜드": ["오클랜드", "퀸스타운"],

    # 중동
    "아랍에미리트": ["두바이", "아부다비"],

    # 아프리카
    "이집트": ["카이로", "룩소르"]
}

# 국가 선택
country = st.selectbox(
    "🌏 여행할 국가를 선택하세요",
    list(travel_destinations.keys())
)

# 도시 선택
destination = st.selectbox(
    "🏙️ 여행할 도시를 선택하세요",
    travel_destinations[country]
)

# 여행 예산 입력
budget = st.number_input(
    "💰 여행 예산을 입력하세요 (원)",
    min_value=0,
    value=1000000,
    step=100000
)

# 여행 기간 선택
days = st.slider(
    "📅 여행 기간은 며칠인가요?",
    min_value=2,
    max_value=14,
    value=4
)



# 여행 스타일 선택
travel_style = st.radio(
    "🎒 어떤 스타일의 여행을 선호하시나요?",
    ["가성비형", "일반형", "럭셔리형"],
    index=1,
    horizontal=True
)

# 스타일별 비용 배율
style_factors = {
    "가성비형": 0.7,
    "일반형": 1.0,
    "럭셔리형": 1.6
}

# 사용자가 선택한 스타일의 배율
factor = style_factors[travel_style]


# 여행지별 비용 데이터 불러오기
df = pd.read_csv("travel_costs.csv")

# 여행 계획 확인 버튼
if st.button("여행 경비 계산하기"):

    # 선택한 국가와 도시의 데이터 찾기
    selected = df[
        (df["country"] == country) &
        (df["city"] == destination)
    ]

    if selected.empty:
        st.warning("아직 해당 도시의 경비 데이터가 준비되지 않았어요.")

    else:
        # 해당 도시의 비용 정보 가져오기
        cost = selected.iloc[0]

        # 항목별 여행 경비 계산
        flight = int(cost["flight"])
        hotel = round(int(cost["hotel"]) * factor * (days - 1))
        food = round(int(cost["food"]) * factor * days)
        transport = int(cost["transport"]) * days
        activity = round(int(cost["activity"]) * factor * days)

        # 전체 예상 경비
        total = flight + hotel + food + transport + activity

        # 남은 예산
        remaining = budget - total

        st.subheader("✈️ 나의 여행 예산 분석")

        st.write(f"여행지: {country} {destination}")
        st.write(f"여행 기간: {days}일")
        st.write(f"예상 총경비: {total:,}원")

        if remaining >= 0:
            st.success(f"예산 내 여행 가능! 남은 금액: {remaining:,}원")
        else:
            st.error(f"예산 부족! 추가 필요 금액: {abs(remaining):,}원")
            
        # ------------------------------------
        # STEP 4. 여행 경비 분석 대시보드
        # ------------------------------------

        st.divider()
        st.subheader("📊 여행 경비 분석 리포트")

        # 1. 핵심 지표(KPI)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="총 예상 경비",
                value=f"{total:,}원"
            )

        with col2:
            st.metric(
                label="설정 예산",
                value=f"{budget:,}원"
            )

        with col3:
            st.metric(
                label="남은 예산",
                value=f"{remaining:,}원"
            )

        # 2. 예산 사용률
        st.subheader("💰 예산 사용률")

        if budget > 0:
            usage_rate = total / budget
            st.progress(min(usage_rate, 1.0))
            st.write(f"예산 사용률: {usage_rate * 100:.1f}%")
        else:
            st.warning("예산이 0원이어서 사용률을 계산할 수 없습니다.")

        # 3. 항목별 지출 데이터
        expense_df = pd.DataFrame({
            "항목": [
                "항공권",
                "숙박비",
                "식비",
                "교통비",
                "관광비"
            ],
            "금액": [
                flight,
                hotel,
                food,
                transport,
                activity
            ]
        })

        # 4. 항목별 지출 막대그래프
        st.subheader("📈 항목별 예상 지출")

        st.bar_chart(
            expense_df.set_index("항목")
        )

        # 5. 항목별 지출 상세표
        st.subheader("📋 상세 경비 내역")

        st.dataframe(
            expense_df,
            hide_index=True,
            use_container_width=True
        )

        # 6. 가장 지출이 큰 항목 분석
        highest = expense_df.loc[
            expense_df["금액"].idxmax()
        ]

        st.info(
            f"가장 지출이 큰 항목은 "
            f"{highest['항목']}이며, "
            f"{highest['금액']:,}원으로 "
            f"전체 경비의 "
            f"{highest['금액'] / total * 100:.1f}%를 차지합니다."
        )
        
        # ------------------------------------
        # STEP 5. 예산 최적화 추천 시스템
        # ------------------------------------

        st.divider()
        st.subheader("💡 나에게 맞는 예산 절약 전략")

        # 1. 여행 조건별 대안 계산
        scenarios = []

        # 시나리오 1: 여행 기간 하루 단축
        if days > 2:
            new_total = calculate_travel_cost(
                cost, days - 1, factor
            )

            scenarios.append({
                "전략": "여행 기간 하루 단축",
                "예상 경비": new_total
            })

        # 시나리오 2: 가성비형으로 변경
        if travel_style != "가성비형":
            new_total = calculate_travel_cost(
                cost, days, 0.7
            )

            scenarios.append({
                "전략": "가성비형으로 변경",
                "예상 경비": new_total
            })

        # 시나리오 3: 관광비 20% 절감
        new_total = calculate_travel_cost(
            cost, days, factor, 0.2
        )

        scenarios.append({
            "전략": "관광비 20% 절감",
            "예상 경비": new_total
        })

        # 시나리오 4: 가성비형 + 하루 단축
        if days > 2 and travel_style != "가성비형":
            new_total = calculate_travel_cost(
                cost, days - 1, 0.7
            )

            scenarios.append({
                "전략": "가성비형 + 하루 단축",
                "예상 경비": new_total
            })

        # 2. 시나리오별 절약액 계산
        scenario_df = pd.DataFrame(scenarios)

        scenario_df["절약 금액"] = (
            total - scenario_df["예상 경비"]
        )

        # 절약이 가능한 전략만 선택
        scenario_df = scenario_df[
            scenario_df["절약 금액"] > 0
        ].copy()

        # 3. 예산 충족 여부 확인
        scenario_df["예산 충족"] = (
            scenario_df["예상 경비"] <= budget
        )

        # 4. 예상 경비가 낮은 순으로 정렬
        scenario_df = scenario_df.sort_values(
            "예상 경비"
        )

        # 5. 결과 출력
        if scenario_df.empty:
            st.info(
                "현재 조건에서 추가로 절약할 수 있는 "
                "시나리오가 없습니다."
            )

        else:
            st.dataframe(
                scenario_df,
                hide_index=True,
                use_container_width=True
            )

            # 예산을 충족하는 전략만 추출
            affordable = scenario_df[
                scenario_df["예산 충족"]
            ]

            if remaining < 0:
                if not affordable.empty:
                    best = affordable.iloc[0]

                    st.success(
                        f"✅ 추천 절약 전략: {best['전략']}\n\n"
                        f"변경 후 예상 경비: "
                        f"{best['예상 경비']:,.0f}원\n\n"
                        f"절약 가능 금액: "
                        f"{best['절약 금액']:,.0f}원"
                    )

                else:
                    st.warning(
                        "현재 절약 시나리오만으로는 "
                        "설정한 예산을 충족하기 어렵습니다. "
                        "여행지나 예산을 조정해 보세요."
                    )

            else:
                st.success(
                    "현재 여행 계획도 예산 내에서 가능합니다! "
                    "아래 절약 전략을 활용하면 "
                    "더 여유로운 여행 예산을 확보할 수 있어요."
                )



# 비용 데이터 불러오기
df = pd.read_csv("travel_costs.csv")

# 선택한 조건 출력
if st.button("여행 계획 확인하기"):
    st.success("여행 조건이 설정되었습니다!")
    st.write(f"여행지: {destination}")
    st.write(f"예산: {budget:,}원")
    st.write(f"여행 기간: {days}일")
    st.write(f"여행 스타일: {travel_style}")
