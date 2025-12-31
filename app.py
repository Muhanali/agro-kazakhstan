import streamlit as st
import ee
import geemap.foliumap as geemap
from streamlit_folium import st_folium
import folium
from folium.plugins import LocateControl
import pandas as pd
import plotly.express as px
import requests
import json

# 1. Настройка страницы
st.set_page_config(layout="wide", page_title="Agro-Monitoring KZ")

# 2. Авторизация в Google Earth Engine
def ee_auth():
    # Пытаемся взять ключ из секретов Streamlit Cloud (для интернета)
    if "gcp_service_account" in st.secrets:
        info = json.loads(st.secrets["gcp_service_account"])
        credentials = ee.ServiceAccountCredentials(info['client_email'], key_data=json.dumps(info))
        ee.Initialize(credentials, project=info['project_id'])
    else:
        # Для работы на локальном компьютере
        ee.Initialize(project='threads-clone-467714')

try:
    ee_auth()
except Exception as e:
    st.error(f"Ошибка авторизации: {e}")

# --- ДАЛЕЕ ВЕСЬ ВАШ КОД ИЗ ПРЕДЫДУЩЕГО ОТВЕТА (Карта, Погода, Графики) ---
# ... (вставьте сюда остальную часть кода)