import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. 获取当前时间
now = datetime.now()
# 2. 定义一个列表来把数字星期转换成中文
weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
weekday_name = weekdays[now.weekday()]
# 3. 拼接成最终格式：2026-05-08 星期五
HEADER_TEXT = f"{now.year}-{now.month:02d}-{now.day:02d} {weekday_name}"

# ================= 1. 核心映射逻辑 =================
def get_channel_mapping(row):
    """根据原文件渠道名和仓库列，返回标准列名"""
    channel = str(row.get('渠道', ''))
    warehouse = str(row.get('仓库', ''))
    
    # 1. 以星海派
    if '以星海派' in channel:
        if '（带车架）' in channel:
            return "以星海派（带车架）"
        else:
            return "以星海派（不带车架）"
    
    # 2. 以星海卡
    elif '以星卡派' in channel:
        if '带车架' in channel:
            return "以星海卡（带车架）"
        else:
            return "以星海卡（不带车架）"
    
    # 3. 普船海派
    elif '普船海派' in channel:
        return "普船海派"
    
    # 4. 普船海卡
    elif '普船LA专线' in channel or '普船NY专线' in channel:
        return "普船海卡"
    
    # 5. ZIM系列
    elif 'ZIM-CA16' in channel:
        return "ZIM-CA16"
    elif 'ZIM-CA9上架保' in channel:
        return "ZIM-CA"
    elif 'ZIM-KY19' in channel:
        return "ZIM-KY19"
    elif 'ZIM-KY23' in channel:
        return "ZIM-KY23"
    elif 'ZIM-KY5卡派' in channel:
        return "ZIM-KY5"
    
    # 6. 普船-CA系列
    elif '普船-CA9卡派' in channel:
        if 'USWC2' in warehouse:
            return "普船-CA2"
        elif 'USWC5' in warehouse:
            return "普船-CA5"
        elif 'USWC' in warehouse:
            return "普船-CA1"
        else:
            return None
    
    # 7. 普船-KY系列
    elif '普船-KY3卡派' in channel or '普船-KY5卡派' in channel:
        return "普船-KY"
    
    # 8. 普船-特惠系列
    elif '普船-KY3特惠卡派' in channel:
        return "普船-特惠KY3"
    elif '普船-KY5特惠卡派' in channel:
        return "普船-特惠KY5"
    
    # 9. 普船-直送系列 (包含合并逻辑)
    elif '普船-USGA直送' in channel or '普船-USGA卡派' in channel:
        return "普船-GA直送"
    elif '普船-USTX直送' in channel or '普船-USTX卡派' in channel:
        return "普船-TX直送"
    elif '普船-USNJ卡派' in channel:
        return "普船-NYC拆送"
    else:
        return None

# ================= 2. 数据处理逻辑 (适配网页版) =================
def process_data(df, city, status, volume_col='体积m3'):
    """处理上传的数据框。"""
    # 1. 筛选城市
    warehouse_col = '国内仓库' if '国内仓库' in df.columns else '仓库'
    if warehouse_col in df.columns:
        df_city = df[df[warehouse_col].str.contains(city, na=False)].copy()
    else:
        st.warning(f"⚠️ {city}表中未找到仓库列")
        return pd.Series()

    # 2. 特殊筛选：如果是“配载”状态，需要筛选开航日期
    if status == '配载':
        sailing_date_col = None
        possible_cols = ['开航日期', '开航时间', '预计开航', 'ETD']
        for col in possible_cols:
            if col in df_city.columns:
                sailing_date_col = col
                break
        if sailing_date_col:
            df_city[sailing_date_col] = pd.to_datetime(df_city[sailing_date_col], errors='coerce')
            # 计算“明天”
            tomorrow = (datetime.now() + timedelta(days=1)).date()
            df_city = df_city[df_city[sailing_date_col].dt.date >= tomorrow]
        else:
            st.info(f"ℹ️ {city}-{status}: 未找到开航日期列，显示所有数据。")

    # 3. 应用映射逻辑
    df_city['标准渠道'] = df_city.apply(get_channel_mapping, axis=1)
    df_valid = df_city[df_city['标准渠道'].notna()]

    # 4. 确保体积列是数值型
    if volume_col in df_valid.columns:
        df_valid[volume_col] = pd.to_numeric(df_valid[volume_col], errors='coerce').fillna(0)
    else:
        st.error(f"❌ 找不到体积列: {volume_col}")
        return pd.Series()

    # 5. 分组求和
    result = df_valid.groupby('标准渠道')[volume_col].sum().round(2)
    return result

# ================= 3. Streamlit 网页界面 =================
st.set_page_config(page_title="🚢 物流数据自动汇总系统", layout="wide")
st.title("🚚 物流数据自动汇总系统 (深圳/上海)")

# 定义最终报表的列顺序
FINAL_COLUMNS = [
    "更新时间",
    "以星海派（带车架）",
    "以星海派（不带车架）",
    "以星海卡（带车架）",
    "以星海卡（不带车架）",
    "普船海派",
    "普船海卡",
    "ZIM-CA",
    "ZIM-CA16",
    "ZIM-KY19",
    "ZIM-KY23",
    "ZIM-KY5",
    "普船-CA1",
    "普船-CA2",
    "普船-CA5",
    "普船-KY",
    "普船-特惠KY3",
    "普船-特惠KY5",
    "普船-NYC拆送",
    "普船-GA直送",
    "普船-TX直送"
]

# 1. 侧边栏上传文件
st.sidebar.header("📂 1. 上传源文件")
uploaded_order = st.sidebar.file_uploader("📥 上传【下单】表", type=['xlsx'])
uploaded_in = st.sidebar.file_uploader("📥 上传【进仓】表", type=['xlsx'])
uploaded_load = st.sidebar.file_uploader("📥 上传【配载】表", type=['xlsx'])

# 2. 主界面处理按钮
if st.sidebar.button("🚀 开始处理数据", type="primary"):
    if not all([uploaded_order, uploaded_in, uploaded_load]):
        st.error("❌ 请上传所有三个文件！")
    else:
        with st.spinner('处理中...请稍候...'):
            # 读取上传的文件
            df_order = pd.read_excel(uploaded_order)
            df_in = pd.read_excel(uploaded_in)
            df_load = pd.read_excel(uploaded_load)

            # 初始化结果存储
            results = {}

            # 遍历六个表格定义 (深圳和上海)
            locations = ["深圳", "上海"]
            statuses = [
                ("下单", "体积m3"),
                ("进仓", "入库体积"),
                ("配载", "入库体积")
            ]

            for city in locations:
                city_data = {}
                for status, vol_col in statuses:
                    sheet_key = f"{city}_{status}"
                    try:
                        # 选择对应的 DataFrame
                        if status == "下单":
                            df = df_order
                        elif status == "进仓":
                            df = df_in
                        else: # 配载
                            df = df_load

                        # 执行处理
                        result_series = process_data(df, city, status, vol_col)
                        
                        # 转换为标准格式的字典
                        result_dict = {col: result_series.get(col, 0) for col in FINAL_COLUMNS}
                        
                        # --- 【关键修复】强制更新第一列时间 ---
                        # 这里必须放在循环内部，否则会被上面的 {col: 0} 覆盖
                        first_column_name = FINAL_COLUMNS[0] 
                        result_dict[first_column_name] = HEADER_TEXT
                        # ------------------------------------
                        
                        city_data[status] = result_dict

                    except Exception as e:
                        st.warning(f"处理 {sheet_key} 时出错: {e}")
                        # 出错时填充0
                        city_data[status] = {col: 0 for col in FINAL_COLUMNS}

                results[city] = city_data

            # 3. 展示结果
            st.success("✅ 数据处理完成！")
            
            # 创建标签页
            tab1, tab2 = st.tabs(["深圳数据", "上海数据"])
            
            with tab1:
                st.subheader("深圳(已下单未进仓)")
                st.dataframe(pd.DataFrame([results['深圳']['下单']]))
                st.subheader("深圳(已进仓未配载)")
                st.dataframe(pd.DataFrame([results['深圳']['进仓']]))
                st.subheader("深圳(已配载未出运)")
                st.dataframe(pd.DataFrame([results['深圳']['配载']]))
            
            with tab2:
                st.subheader("上海(已下单未进仓)")
                st.dataframe(pd.DataFrame([results['上海']['下单']]))
                st.subheader("上海(已进仓未配载)")
                st.dataframe(pd.DataFrame([results['上海']['进仓']]))
                st.subheader("上海(已配载未出运)")
                st.dataframe(pd.DataFrame([results['上海']['配载']]))

            # 底部说明
            st.markdown("---")
            st.markdown("*提示：该工具会自动识别深圳/上海仓库，并按标准渠道映射体积。*")