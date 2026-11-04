
import re
from itertools import combinations

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide",
)

CSV_URL = (
    "https://raw.githubusercontent.com/it-teacher-go/"
    "data-share-/main/songtan_meals_184.csv"
)

st.title("급식 규칙 찾기")
st.caption("송탄고 중식 데이터를 이용해 함께 나오는 메뉴 규칙을 분석합니다.")


@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL, encoding="utf-8")

    required = ["날짜", "식사", "메뉴"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(
            f"CSV에 필요한 열이 없습니다: {', '.join(missing)}"
        )

    df = df[required].copy()
    df = df[
        (df["식사"].astype(str).str.strip() == "중식")
        & df["메뉴"].notna()
    ].copy()

    return df


def clean_menu(name):
    """메뉴 이름에서 괄호와 괄호 안 내용을 제거한다."""
    name = str(name).strip()

    # 괄호가 중첩된 경우에도 괄호 구간을 제거
    previous = None
    while previous != name:
        previous = name
        name = re.sub(r"\([^()]*\)", "", name)
        name = re.sub(r"\[[^\[\]]*\]", "", name)
        name = re.sub(r"\{[^{}]*\}", "", name)

    return re.sub(r"\s+", " ", name).strip()


try:
    raw_df = load_data()
except Exception as e:
    st.error(f"CSV 데이터를 불러오지 못했습니다: {e}")
    st.stop()


# 하루 식단 하나를 장바구니 한 건으로 처리
baskets = []

for _, row in raw_df.iterrows():
    menus = {
        clean_menu(item)
        for item in str(row["메뉴"]).split("|")
        if clean_menu(item)
    }

    if menus:
        baskets.append(menus)

if not baskets:
    st.warning("분석할 중식 데이터가 없습니다.")
    st.stop()

total_days = len(baskets)
menu_counts = {}

for basket in baskets:
    for menu in basket:
        menu_counts[menu] = menu_counts.get(menu, 0) + 1

total_menus = len(menu_counts)

# 같은 날 함께 나온 메뉴 쌍의 횟수
pair_counts = {}

for basket in baskets:
    for a, b in combinations(sorted(basket), 2):
        pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1

total_pairs = len(pair_counts)

# 연관 규칙 생성: A -> B, B -> A 모두 생성
rules = []

for (a, b), count in pair_counts.items():
    support = count / total_days

    confidence_ab = count / menu_counts[a]
    confidence_ba = count / menu_counts[b]

    lift_ab = confidence_ab / (menu_counts[b] / total_days)
    lift_ba = confidence_ba / (menu_counts[a] / total_days)

    rules.append({
        "조건": a,
        "결과": b,
        "동시": count,
        "지지도": support,
        "신뢰도": confidence_ab,
        "향상도": lift_ab,
    })

    rules.append({
        "조건": b,
        "결과": a,
        "동시": count,
        "지지도": support,
        "신뢰도": confidence_ba,
        "향상도": lift_ba,
    })

rules_df = pd.DataFrame(
    rules,
    columns=["조건", "결과", "동시", "지지도", "신뢰도", "향상도"],
)

st.subheader("데이터 요약")

c1, c2, c3 = st.columns(3)
c1.metric("급식 일수", f"{total_days}일")
c2.metric("메뉴 종류 수", f"{total_menus}개")
c3.metric("함께 나온 메뉴 쌍", f"{total_pairs}쌍")

st.divider()
st.subheader("연관 규칙")

sort_option = st.selectbox(
    "정렬 기준",
    ["향상도 순", "신뢰도 순", "동시 순"],
    key="sort_option",
)

sort_columns = {
    "향상도 순": ["향상도", "신뢰도", "동시"],
    "신뢰도 순": ["신뢰도", "향상도", "동시"],
    "동시 순": ["동시", "향상도", "신뢰도"],
}

all_menus = sorted(menu_counts.keys())

selected_menu = st.selectbox(
    "메뉴로 좁혀 보기",
    ["전체 메뉴"] + all_menus,
    key="menu_filter",
)

filtered_df = rules_df.copy()

if selected_menu != "전체 메뉴":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]

filtered_df = filtered_df.sort_values(
    sort_columns[sort_option],
    ascending=[False, False, False],
).reset_index(drop=True)

st.write(f"표에 표시되는 규칙: **{len(filtered_df)}개**")

display_df = filtered_df.copy()

for col in ["지지도", "신뢰도", "향상도"]:
    display_df[col] = display_df[col].map(lambda x: f"{x:.3f}")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "지지도 = 두 메뉴가 함께 나온 일수 ÷ 전체 급식 일수 / "
    "신뢰도 = 조건 메뉴가 나온 날 중 결과 메뉴도 나온 비율 / "
    "향상도 = 신뢰도 ÷ 결과 메뉴의 전체 등장 비율"
)

st.divider()
st.subheader("향상도 상위 10개 규칙")

chart_df = filtered_df.sort_values(
    ["향상도", "신뢰도", "동시"],
    ascending=[False, False, False],
).head(10).copy()

if chart_df.empty:
    st.info("현재 메뉴 조건에 해당하는 규칙이 없습니다.")
else:
    chart_df["규칙"] = chart_df["조건"] + " → " + chart_df["결과"]
    chart_df = chart_df.sort_values("향상도", ascending=True)

    fig = px.bar(
        chart_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.3f",
            "신뢰도": ":.3f",
            "향상도": ":.3f",
            "규칙": False,
        },
        labels={
            "향상도": "향상도",
            "규칙": "연관 규칙",
        },
        title="향상도 상위 10개",
    )

    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        yaxis_title="",
        xaxis_title="향상도",
        height=max(350, len(chart_df) * 42),
        margin=dict(l=20, r=50, t=60, b=30),
    )

    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "분석 기준: 하루 식단을 한 건으로 계산하며, "
    "메뉴 이름의 괄호와 괄호 안 내용은 제외합니다."
)
