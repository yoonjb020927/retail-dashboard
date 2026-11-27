import streamlit as st  # 화면을 만드는 라이브러리
import pandas as pd  # 표 데이터를 다루는 라이브러리 (Python 안의 엑셀)

DATA_FILE = "retail_rate.csv"  # 데이터 파일 이름 (app.py와 같은 폴더, 상대경로)
REQUIRED_COLUMNS = ["year_month", "C1_NM", "ITM_NM", "retail_index", "base_rate"]  # 꼭 있어야 하는 열
DEFAULT_ITEMS = ["승용차", "가전제품", "의복", "음식료품"]  # 처음 화면에 보여 줄 대표 품목

# 품목마다 붙일 재 종류 꼬리표 (기말과제_프로젝트_이해정리.md 분류표 기준)
ITEM_GROUP = {
    "승용차": "내구재", "가전제품": "내구재", "통신기기 및 컴퓨터": "내구재",
    "가구": "내구재", "기타내구재": "내구재",
    "의복": "준내구재", "신발 및 가방": "준내구재", "오락 취미 경기용품": "준내구재",
    "기타준내구재": "준내구재",
    "음식료품": "비내구재", "의약품": "비내구재", "화장품": "비내구재",
    "서적 문구": "비내구재", "차량연료": "비내구재", "기타비내구재": "비내구재",
}


def add_group_tag(name: str) -> str:
    """'승용차' → '승용차(내구재)'처럼 품목 이름 뒤에 재 종류를 붙인다. 목록에 없으면 그대로 둔다."""
    return f"{name}({ITEM_GROUP[name]})" if name in ITEM_GROUP else name

st.set_page_config(page_title="금리와 소비 대시보드", layout="wide")  # 브라우저 탭 제목, 넓은 화면
st.title("기준금리와 품목별 소매판매")  # 맨 위 제목
st.caption(
    "데이터 출처: 통계청 KOSIS 소매판매액지수(2020=100), 한국은행 ECOS 기준금리 · "
    "기간 2015-01 ~ 2026-09 · 수집일 2026-11-25"
)


# ---------- 1. 데이터 불러오기 ----------
@st.cache_data  # 한 번 읽은 CSV를 기억해 두고, 조건을 바꿀 때 다시 읽지 않는다
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")  # CSV를 표(DataFrame)로 읽기, 한글 깨짐 방지


try:
    raw = load_data(DATA_FILE)
except FileNotFoundError:  # 파일이 없을 때 빨간 에러 대신 안내
    st.error(f"'{DATA_FILE}' 파일을 찾을 수 없습니다. app.py와 같은 폴더에 파일이 있는지 확인해 주세요.")
    st.stop()

missing = [col for col in REQUIRED_COLUMNS if col not in raw.columns]  # 없는 열 찾기
if missing:
    st.error(f"CSV에 다음 열이 없습니다: {', '.join(missing)}. 열 이름을 확인해 주세요.")
    st.stop()

# 필요한 열만 골라 알아보기 쉬운 한글 이름으로 바꾼 새 표
df = raw[REQUIRED_COLUMNS].rename(
    columns={"C1_NM": "품목", "ITM_NM": "지수종류", "retail_index": "판매지수", "base_rate": "기준금리"}
)
df = df.assign(연월=pd.to_datetime(df["year_month"].astype(str), format="%Y%m").dt.strftime("%Y-%m"))
df = df.assign(품목=df["품목"].map(add_group_tag))  # 품목 이름에 꼬리표 붙이기 → 사이드바·그래프·표에 모두 반영


# ---------- 2. 사이드바 조건(필터) ----------
st.sidebar.header("조건 선택")

item_options = [add_group_tag(name) for name in ITEM_GROUP]  # 품목 15개, ITEM_GROUP에 적은 순서(내구재→준내구재→비내구재)대로
default_items = [add_group_tag(name) for name in DEFAULT_ITEMS]  # 기본값도 꼬리표 붙은 이름으로 맞춘다
items = st.sidebar.multiselect("품목 (여러 개 선택)", item_options, default=default_items)

index_type = st.sidebar.radio(
    "지수 종류", ["계절조정지수", "불변지수"], help="계절조정: 명절·계절 효과를 뺀 값 / 불변: 물가 효과를 뺀 값"
)

month_options = sorted(df["연월"].unique())  # 2015-01 ~ 2026-09
start_month, end_month = st.sidebar.select_slider(
    "기간", options=month_options, value=(month_options[0], month_options[-1])
)

# 세 조건을 모두 만족하는 행만 남긴 표 = filtered
filtered = df[
    df["품목"].isin(items)  # 고른 품목 중 하나인가
    & (df["지수종류"] == index_type)  # 고른 지수 종류인가
    & df["연월"].between(start_month, end_month)  # 기간 안인가 ('2015-01' 같은 글자는 순서대로 비교됨)
]

st.sidebar.write(f"선택 조건: **{len(filtered)}건** / 전체 {len(df)}건")


# ---------- 3. 0건 처리 ----------
# 필터 바로 아래, 지표·그래프보다 먼저 검사한다
if filtered.empty:
    st.info("조건에 맞는 데이터가 0건입니다. 품목을 하나 이상 골라 보세요.")
    st.stop()  # 여기서 화면 그리기를 멈춘다 → 아래 지표·그래프·표는 그리지 않음


# ---------- 4. 지표 카드 ----------
by_month = filtered.pivot_table(index="연월", columns="품목", values="판매지수")  # 행=월, 열=품목
rate_by_month = filtered.groupby("연월")["기준금리"].first()  # 같은 달은 금리가 같으므로 첫 값만

first_avg = by_month.iloc[0].mean()  # 시작 달의 선택 품목 평균 지수
last_avg = by_month.iloc[-1].mean()  # 마지막 달의 선택 품목 평균 지수
change_pct = (last_avg / first_avg - 1) * 100  # 기간 중 변화율(%)
rate_change = rate_by_month.iloc[-1] - rate_by_month.iloc[0]  # 기간 중 금리 변화(%p)

col1, col2, col3 = st.columns(3)
col1.metric("최근 판매지수", f"{last_avg:.1f}", f"{change_pct:+.1f}%")  # 이름이 길면 좁은 화면에서 잘려서 짧게
col2.metric("최근 기준금리", f"{rate_by_month.iloc[-1]:.2f}%", f"{rate_change:+.2f}%p", delta_color="inverse")
col3.metric("기간 평균 지수", f"{filtered['판매지수'].mean():.1f}")
st.caption(f"최근 = 선택 기간의 마지막 달({end_month}) · 화살표 = 첫 달({start_month}) 대비 변화 · 판매지수는 선택 품목의 평균")


# ---------- 5. 그래프 ----------
st.subheader("품목별 판매지수 추이")
st.line_chart(by_month)  # 시간에 따른 변화 → 선 그래프 (품목마다 선 하나)

left, right = st.columns(2)
with left:
    st.subheader("기준금리 추이 (%)")
    st.line_chart(rate_by_month)  # 금리가 언제 오르고 내렸는지
with right:
    st.subheader("품목별 기간 변화율 (%)")
    item_change = ((by_month.iloc[-1] / by_month.iloc[0] - 1) * 100).sort_values()  # 품목마다 시작→끝 변화율
    st.bar_chart(item_change)  # 항목끼리 크기 비교 → 막대 그래프


# ---------- 6. 상세 표 ----------
st.subheader("상세 데이터")
table = filtered[["연월", "품목", "지수종류", "판매지수", "기준금리"]].sort_values(["연월", "품목"])
st.dataframe(table, hide_index=True, width="stretch")  # 표를 화면 폭에 맞춤


# ---------- 7. 경영 판단 ----------
best, worst = item_change.idxmax(), item_change.idxmin()  # 변화율이 가장 높은 품목, 가장 낮은 품목
st.subheader("이 화면으로 내릴 수 있는 경영 판단")
st.write(
    f"{start_month}~{end_month} 동안 기준금리는 {rate_change:+.2f}%p 바뀌었습니다. "
    f"선택 품목 중 판매지수 변화율이 가장 높은 품목은 **{best}**({item_change[best]:+.1f}%), "
    f"가장 낮은 품목은 **{worst}**({item_change[worst]:+.1f}%)입니다. "
    "기간을 금리 인상기(2021-08~2023-01)로 좁혀 판매가 줄어드는 품목을 찾으면, "
    "그 품목이 할부·프로모션 같은 금리 부담 완화 판촉을 먼저 검토할 대상입니다."
)
