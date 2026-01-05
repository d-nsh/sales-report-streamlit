import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Отчёт по продажам", layout="centered")
st.title("📊 Автоматический отчёт по продажам")

uploaded_file = st.file_uploader(
    "Загрузите Excel-файл с продажами",
    type=["xlsx"]
)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        COLUMN_MAP = {
    "Дата": ["дата", "date", "дата продажи", "sale date"],
    "Товар": ["товар", "product", "название", "наименование"],
    "Категория": ["категория", "category", "группа"],
    "Цена": ["цена", "price", "стоимость", "cost"],
    "Количество": ["количество", "qty", "quantity", "count", "штук"]
}

        normalized_cols = {col.lower(): col for col in df.columns}
        rename_dict = {}

        for standard_col, variants in COLUMN_MAP.items():
            for variant in variants:
                if variant in normalized_cols:
                    rename_dict[normalized_cols[variant]] = standard_col
                    break

        df = df.rename(columns=rename_dict)
        if rename_dict:
            st.success("Распознаны столбцы:")
            st.json(rename_dict)
        # Проверка наличия обязательных столбцов
        required_cols = list(COLUMN_MAP.keys())
        missing = [col for col in required_cols if col not in df.columns]

        if missing:
            st.error(
        "❌ Не удалось найти столбцы: " + ", ".join(missing) +
        "\n\nПроверьте названия столбцов или обратитесь за адаптацией."
    )
            st.stop()

        # Приведение типов
        df['Дата'] = pd.to_datetime(df['Дата'], dayfirst=True, errors='coerce')
        df['Цена'] = pd.to_numeric(df['Цена'], errors='coerce')
        df['Количество'] = pd.to_numeric(df['Количество'], errors='coerce')
        df = df.dropna(subset=required_cols)
        st.subheader("⚙️ Настройки отчёта")

        use_bad_words_filter = st.checkbox(
            "Исключать тестовые и ошибочные товары",
            value=True
            )

        show_category_table = st.checkbox(
            "Показать отчёт по категориям",
            value=True
            )

        show_chart = st.checkbox(
            "Показать график по категориям",
            value=True
            )

        st.subheader("📅 Выбор периода")

        min_date = df['Дата'].min().date()
        max_date = df['Дата'].max().date()

        start_date, end_date = st.date_input(
            "Период анализа",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        df = df[
            (df["Дата"] >= pd.to_datetime(start_date)) &
            (df["Дата"] <= pd.to_datetime(end_date))
        ]

        # Расчёт выручки
        df["Выручка"] = df["Цена"] * df["Количество"]

        # Фильтр мусорных товаров
        if use_bad_words_filter:
           bad_words = ["ошибка", "тест", "demo", "sample"]
           mask = ~df["Товар"].str.lower().str.contains("|".join(bad_words))
           df = df[mask]
        if df.empty:
            st.warning("❗ По выбранным условиям данных нет")
            st.stop()
        # ===== Итоговый отчёт =====
        summary = pd.DataFrame({
            "Показатель": [
                "Общая выручка",
                "Количество продаж",
                "Количество категорий",
                "Дата начала",
                "Дата окончания"
            ],
            "Значение": [
                df["Выручка"].sum(),
                len(df),
                df["Категория"].nunique(),
                df["Дата"].min().date(),
                df["Дата"].max().date()
            ]
        })

        st.subheader("📌 Общие показатели")
        st.dataframe(summary, use_container_width=True)

        # ===== Отчёт по категориям =====
        report_by_category = (
            df.groupby("Категория", as_index=False)["Выручка"]
            .sum()
            .sort_values(by="Выручка", ascending=False)
        )

        if show_category_table:
            st.subheader("📦 Выручка по категориям")
            st.dataframe(report_by_category, use_container_width=True)
        if show_chart:
           st.subheader("📊 График выручки по категориям")
           chart_data = report_by_category.set_index("Категория")["Выручка"]
           st.bar_chart(chart_data)

        # ===== Выгрузка Excel =====
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            summary.to_excel(writer, sheet_name="Итоги", index=False)
            report_by_category.to_excel(writer, sheet_name="По категориям", index=False)

        buffer.seek(0)

        st.download_button(
            label="📥 Скачать Excel-отчёт",
            data=buffer,
            file_name="Отчет_по_продажам.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error("Ошибка при обработке файла")
        st.exception(e)
