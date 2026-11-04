import streamlit as st
import pandas as pd
from itertools import combinations
from collections import Counter

st.set_page_config(
    page_title="급식 메뉴 동시 출현 분석",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 메뉴 동시 출현 분석")
st.write("같은 날 나온 메뉴의 관계와 함께 나온 적 없는 메뉴를 분석합니다.")

uploaded_file = st.file_uploader(
    "급식 데이터 CSV 파일 업로드",
    type=["csv"]
)

if uploaded_file is None:
    st.info("분석할 급식 CSV 파일을 업로드해 주세요.")
    st.stop()

try:
    df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
except Exception:
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, encoding="cp949")

st.subheader("데이터 확인")
st.dataframe(df.head(), use_container_width=True)

date_col = st.selectbox(
    "날짜 열 선택",
    options=df.columns,
    key="date_column"
)

menu_col = st.selectbox(
    "메뉴 열 선택",
    options=df.columns,
    key="menu_column"
)

if date_col == menu_col:
    st.error("날짜 열과 메뉴 열을 서로 다르게 선택해 주세요.")
    st.stop()


def split_menus(value):
    if pd.isna(value):
        return []

    text = str(value)

    for separator in ["\n", ",", "/", ";", "|"]:
        text = text.replace(separator, "\n")

    return [
        item.strip()
        for item in text.split("\n")
        if item.strip()
    ]


work = df[[date_col, menu_col]].copy()
work[date_col] = pd.to_datetime(
    work[date_col],
    errors="coerce"
).dt.date

work = work.dropna(subset=[date_col, menu_col])

daily_menus = {}

for date, group in work.groupby(date_col):
    menus = set()

    for value in group[menu_col]:
        menus.update(split_menus(value))

    if menus:
        daily_menus[date] = menus

if not daily_menus:
    st.warning("분석할 날짜와 메뉴 데이터가 없습니다.")
    st.stop()

# 메뉴별 등장 일수
menu_days = Counter()

for menus in daily_menus.values():
    menu_days.update(menus)

# 메뉴 쌍별 동시 등장 일수
pair_days = Counter()

for menus in daily_menus.values():
    for a, b in combinations(sorted(menus), 2):
        pair_days[(a, b)] += 1

st.divider()
st.subheader("1. 함께 나온 메뉴 규칙")

min_days = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1
)

rules = []

for (a, b), count in pair_days.items():
    if count >= min_days:
        rules.append({
            "메뉴 1": a,
            "메뉴 2": b,
            "동시 등장 일수": count,
            "메뉴 1 등장 일수": menu_days[a],
            "메뉴 2 등장 일수": menu_days[b]
        })

rules_df = pd.DataFrame(rules)

if not rules_df.empty:
    rules_df = rules_df.sort_values(
        ["동시 등장 일수", "메뉴 1", "메뉴 2"],
        ascending=[False, True, True]
    ).reset_index(drop=True)

st.write(f"현재 조건에서 남은 규칙은 **{len(rules_df)}개**입니다.")

if rules_df.empty:
    st.info("선택한 최소 동시 일수를 만족하는 규칙이 없습니다.")
else:
    st.dataframe(rules_df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("2. 함께 나온 적 없는 짝")

st.write(
    "메뉴를 선택하면 같은 날 한 번도 함께 나오지 않은 메뉴 중 "
    "각각 10일 이상 등장한 메뉴를 보여 줍니다."
)

all_menus = sorted(menu_days.keys())

selected_menu = st.selectbox(
    "함께 나온 적 없는 짝을 찾을 메뉴",
    options=all_menus,
    key="never_together_menu"
)

never_together = []

for other_menu in all_menus:
    if other_menu == selected_menu:
        continue

    pair = tuple(sorted([selected_menu, other_menu]))

    if pair_days.get(pair, 0) == 0 and menu_days[other_menu] >= 10:
        never_together.append({
            "메뉴": other_menu,
            "등장 일수": menu_days[other_menu]
        })

never_df = pd.DataFrame(never_together)

st.write(
    f"**{selected_menu}** 메뉴는 총 "
    f"**{menu_days[selected_menu]}일** 등장했습니다."
)

if never_df.empty:
    st.info(
        "함께 나온 적이 없고, 각각 10일 이상 등장한 메뉴가 없습니다."
    )
else:
    never_df = never_df.sort_values(
        ["등장 일수", "메뉴"],
        ascending=[False, True]
    ).reset_index(drop=True)

    st.write(f"조건에 맞는 메뉴는 **{len(never_df)}개**입니다.")
    st.dataframe(never_df, use_container_width=True, hide_index=True)

st.caption(
    "참고: 메뉴 열에 여러 메뉴가 한 셀에 들어 있다면 "
    "쉼표, 슬래시, 줄바꿈 등의 구분자로 분리합니다."
)
