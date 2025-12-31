import streamlit as st
import ee
import geemap.foliumap as geemap
from streamlit_folium import st_folium
import folium
from folium.plugins import LocateControl
import pandas as pd
import plotly.express as px
import requests

# 1. Настройка страницы
st.set_page_config(layout="wide", page_title="Агро-Мониторинг Казахстан")

# 2. Инициализация Google Earth Engine
try:
    ee.Initialize(project='threads-clone-467714')
except Exception as e:
    st.error(f"Ошибка авторизации Google: {e}")

# 3. Сохранение координат в памяти браузера
if 'lat' not in st.session_state:
    st.session_state.lat = 51.1600  # Начальная точка (Астана)
if 'lon' not in st.session_state:
    st.session_state.lon = 71.3800

# --- ИНТЕРФЕЙС ---
st.title("🛰️ Спутниковый мониторинг полей Казахстана")

# Разделяем экран: Карта (слева) и Погода (справа)
col_map, col_side = st.columns([4, 1])

with col_map:
    # Выбор показателя прямо над картой
    index_choice = st.segmented_control(
        "Выберите слой анализа:",
        ["Здоровье (NDVI)", "Влага (NDWI)", "Азот (NDRE)", "Хлорофилл"],
        default="Здоровье (NDVI)"
    )
    
    # Создание карты
    m = geemap.Map(center=[st.session_state.lat, st.session_state.lon], zoom=13)
    
    # ДОБАВЛЯЕМ КНОПКУ ОПРЕДЕЛЕНИЯ ЛОКАЦИИ
    LocateControl(auto_start=False, flyTo=True, keepCurrentZoomLevel=True).add_to(m)

    # Логика работы со спутником
    point = ee.Geometry.Point([st.session_state.lon, st.session_state.lat])
    roi = point.buffer(2000).bounds()

    # Загружаем свежий снимок Sentinel-2
    image = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(roi) \
        .filterDate('2025-05-01', '2025-09-30') \
        .sort('CLOUDY_PIXEL_PERCENTAGE') \
        .first()

    if image:
        if index_choice == "Здоровье (NDVI)":
            res_img = image.normalizedDifference(['B8', 'B4'])
            vis = {'min': 0, 'max': 0.8, 'palette': ['red', 'yellow', 'green']}
        elif index_choice == "Влага (NDWI)":
            res_img = image.normalizedDifference(['B8', 'B11'])
            vis = {'min': -0.1, 'max': 0.5, 'palette': ['#ece7f2', '#a6bddb', '#2b8cbe']}
        elif index_choice == "Азот (NDRE)":
            res_img = image.normalizedDifference(['B8', 'B5'])
            vis = {'min': 0, 'max': 0.5, 'palette': ['#f7fcb9', '#addd8e', '#31a354']}
        else: # Хлорофилл
            res_img = image.expression('B8 / B3 - 1', {'B8': image.select('B8'), 'B3': image.select('B3')})
            vis = {'min': 0, 'max': 5, 'palette': ['white', 'blue', 'darkgreen']}

        m.addLayer(res_img.clip(roi), vis, index_choice)
    
    # Ставим маркер в выбранную точку
    m.add_marker([st.session_state.lat, st.session_state.lon], tooltip="Выбранное поле")

    # ОТОБРАЖЕНИЕ КАРТЫ (Большой размер)
    map_data = st_folium(m, width="100%", height=650, key="main_map")

    # Если кликнули мышкой — обновляем всё приложение
    if map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]
        if new_lat != st.session_state.lat or new_lon != st.session_state.lon:
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            st.rerun()

with col_side:
    st.subheader("☁️ Погода")
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={st.session_state.lat}&longitude={st.session_state.lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        w_data = requests.get(w_url).json()
        st.metric("Темп.", f"{w_data['current']['temperature_2m']}°C")
        st.metric("Влажн.", f"{w_data['current']['relative_humidity_2m']}%")
        st.metric("Ветер", f"{w_data['current']['wind_speed_10m']} км/ч")
        st.caption(f"Координаты: \n{st.session_state.lat:.4f}, {st.session_state.lon:.4f}")
    except:
        st.write("Загрузка погоды...")

# --- НИЖНЯЯ ПАНЕЛЬ: МАЛЕНЬКИЙ ГРАФИК ---
st.divider()
st.subheader("📊 История роста (NDVI) за сезон")

col_graph, col_spacer = st.columns([2, 1])

with col_graph:
    with st.spinner("Загрузка истории снимков..."):
        history = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(point) \
            .filterDate('2025-03-01', '2025-11-01') \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))

        def get_val(img):
            v = img.normalizedDifference(['B8', 'B4']).reduceRegion(ee.Reducer.mean(), point, 20).get('nd')
            return ee.Feature(None, {'date': img.date().format('YYYY-MM-dd'), 'val': v})

        hist_data = history.map(get_val).filter(ee.Filter.notNull(['val'])).getInfo()
        
        if hist_data['features']:
            df = pd.DataFrame([f['properties'] for f in hist_data['features']])
            # Компактный график
            fig = px.line(df, x='date', y='val', template="plotly_white")
            fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
            fig.update_traces(line_color='#2ca02c', fill='tozeroy')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нажмите на карту, чтобы увидеть историю этого места.")