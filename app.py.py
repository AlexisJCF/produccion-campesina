import streamlit as st
from supabase import create_client, Client
from datetime import date
import os
from dotenv import load_dotenv

# Cargar variables de entorno (para desarrollo local)
load_dotenv()

# Inicializar cliente de Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

st.set_page_config(page_title="COOPROGRESO - Capacidad Productiva", layout="wide")
st.title("🌾 Formulario de Capacidad Productiva")
st.markdown("Completa los datos solicitados. Los campos con * son obligatorios.")

# ========== SESSION STATE para almacenar datos mientras se navega ==========
if "step" not in st.session_state:
    st.session_state.step = 1
if "survey_id" not in st.session_state:
    st.session_state.survey_id = None
if "temp_data" not in st.session_state:
    st.session_state.temp_data = {}

# ========== FUNCIÓN PARA GUARDAR EN SUPABASE ==========
def save_survey(data):
    # 1. Insertar registro principal
    survey_data = {
        "registration_date": data["registration_date"],
        "type": data["type"],
        "reason": data["reason"],
        "signature": data.get("signature", False)
    }
    result = supabase.table("survey_registry").insert(survey_data).execute()
    survey_id = result.data[0]["id"]
    
    # 2. Familiares (pueden ser varios)
    for member in data["family_members"]:
        member["survey_id"] = survey_id
        supabase.table("family_members").insert(member).execute()
    
    # 3. Vivienda
    housing_data = data["housing"]
    housing_data["survey_id"] = survey_id
    supabase.table("housing").insert(housing_data).execute()
    
    # 4. Predio
    land_data = data["land"]
    land_data["survey_id"] = survey_id
    supabase.table("land").insert(land_data).execute()
    
    # 5. Producciones
    for prod in data["productions"]:
        prod["survey_id"] = survey_id
        supabase.table("production_capacity").insert(prod).execute()
    
    # 6. Servicios
    for serv in data["services"]:
        serv["survey_id"] = survey_id
        supabase.table("service_capacity").insert(serv).execute()
    
    return survey_id

# ========== PASO 1: Datos generales y productor principal ==========
def step1():
    st.header("📋 Paso 1: Datos del levantamiento y productor principal")
    
    with st.form("step1_form"):
        col1, col2 = st.columns(2)
        with col1:
            reg_date = st.date_input("Fecha de registro *", value=date.today())
            reg_type = st.selectbox("Tipo *", ["INICIAL", "ACTUAL"])
        with col2:
            reason = st.text_area("Razón del levantamiento")
            signature = st.checkbox("Firma del productor asociado")
        
        st.subheader("👤 Productor principal (cooperante)")
        col1, col2, col3 = st.columns(3)
        with col1:
            nombres = st.text_input("Nombres *")
            apellidos = st.text_input("Apellidos *")
            parentesco = st.text_input("Parentesco (auto)", value="Principal", disabled=True)
        with col2:
            birth = st.date_input("Fecha nacimiento", value=None)
            id_num = st.text_input("Número de identificación *")
            id_place = st.text_input("Lugar expedición")
        with col3:
            phone = st.text_input("Teléfono/Celular")
            email = st.text_input("Email")
            sisben_id = st.text_input("# Ficha Sisbén")
            sisben_cat = st.selectbox("Categoría Sisbén", ["A1","A2","B1","B2","C","D","E","No aplica"])
        
        nivel = st.selectbox("Nivel escolar", ["Ninguno","Primaria","Secundaria","Técnico","Tecnólogo","Profesional","Posgrado"])
        disciplina = st.text_input("Disciplina / Oficio")
        ocupacion = st.text_input("Ocupación actual")
        
        submitted = st.form_submit_button("Siguiente →")
        if submitted:
            if nombres and apellidos and id_num:
                st.session_state.temp_data.update({
                    "registration_date": reg_date,
                    "type": reg_type,
                    "reason": reason,
                    "signature": signature,
                    "family_members": [{
                        "is_main": True,
                        "nombres": nombres,
                        "apellidos": apellidos,
                        "parentesco": "Principal",
                        "birth_date": birth,
                        "id_number": id_num,
                        "id_issue_place": id_place,
                        "phone": phone,
                        "email": email,
                        "education_level": nivel,
                        "discipline": disciplina,
                        "occupation": ocupacion,
                        "sisben_id": sisben_id,
                        "sisben_category": sisben_cat
                    }]
                })
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Nombres, apellidos e identificación del productor principal son obligatorios.")

# ========== PASO 2: Otros familiares ==========
def step2():
    st.header("👨‍👩‍👧‍👦 Paso 2: Otros miembros de la familia")
    st.info("Agrega los demás integrantes de la unidad familiar (opcional).")
    
    if "extra_family" not in st.session_state:
        st.session_state.extra_family = []
    
    # Mostrar familiares ya agregados
    for i, m in enumerate(st.session_state.extra_family):
        with st.expander(f"{m.get('nombres','')} {m.get('apellidos','')} - {m.get('parentesco','')}"):
            st.write(f"Teléfono: {m.get('phone','')}")
            if st.button(f"Eliminar", key=f"del_fam_{i}"):
                st.session_state.extra_family.pop(i)
                st.rerun()
    
    # Formulario para agregar nuevo familiar
    with st.form("add_family_form"):
        col1, col2 = st.columns(2)
        with col1:
            fam_nombres = st.text_input("Nombres")
            fam_apellidos = st.text_input("Apellidos")
            fam_parentesco = st.text_input("Parentesco (ej: cónyuge, hijo, madre)")
        with col2:
            fam_birth = st.date_input("Fecha nacimiento", value=None)
            fam_phone = st.text_input("Teléfono")
            fam_ocupacion = st.text_input("Ocupación")
        
        fam_nivel = st.selectbox("Nivel escolar", ["","Ninguno","Primaria","Secundaria","Técnico","Tecnólogo","Profesional","Posgrado"])
        
        add = st.form_submit_button("➕ Agregar familiar")
        if add and fam_nombres and fam_apellidos:
            st.session_state.extra_family.append({
                "is_main": False,
                "nombres": fam_nombres,
                "apellidos": fam_apellidos,
                "parentesco": fam_parentesco,
                "birth_date": fam_birth,
                "id_number": "",
                "id_issue_place": "",
                "phone": fam_phone,
                "email": "",
                "education_level": fam_nivel,
                "discipline": "",
                "occupation": fam_ocupacion,
                "sisben_id": "",
                "sisben_category": ""
            })
            st.rerun()
    
    col_b, col_n = st.columns(2)
    with col_b:
        if st.button("← Atrás"):
            st.session_state.step = 1
            st.rerun()
    with col_n:
        if st.button("Siguiente →"):
            # Guardar familiares adicionales en temp_data
            st.session_state.temp_data["family_members"].extend(st.session_state.extra_family)
            st.session_state.step = 3
            st.rerun()

# ========== PASO 3: Vivienda y Predio ==========
def step3():
    st.header("🏠 Paso 3: Vivienda y Predio")
    with st.form("housing_land_form"):
        st.subheader("Datos de la vivienda")
        col1, col2 = st.columns(2)
        with col1:
            housing_type = st.text_input("Tipo de propiedad (vivienda)", help="Ej: propia, arrendada, familiar")
            housing_loc = st.text_input("Ubicación geográfica (vereda, corregimiento)")
            housing_cat = st.text_input("ID Catastral")
        with col2:
            built_area = st.number_input("Área construida (m²)", min_value=0.0, step=10.0)
            patio_area = st.number_input("Área de patio (m²)", min_value=0.0, step=10.0)
        
        st.subheader("Calidades básicas (vivienda)")
        colq1, colq2, colq3 = st.columns(3)
        with colq1:
            water_q = st.selectbox("Calidad del agua", ["Buena","Regular","Mala","No tiene"])
            energy_q = st.selectbox("Calidad energía", ["Buena","Regular","Mala","No tiene"])
        with colq2:
            internet_q = st.selectbox("Calidad internet", ["Buena","Regular","Mala","No tiene"])
            sewage = st.selectbox("Alcantarillado", ["Si","No","Pozo séptico","Letrina"])
        with colq3:
            waste = st.selectbox("Recolección de aseo", ["Si","No","Quema","Entierro"])
        
        st.subheader("🌳 Datos del predio (tierra de cultivo, pesca, etc.)")
        colL1, colL2 = st.columns(2)
        with colL1:
            land_prop_type = st.text_input("Tipo propiedad del predio")
            land_name = st.text_input("Nombre del predio")
            land_loc = st.text_input("Ubicación del predio")
        with colL2:
            land_cat = st.text_input("ID Catastral del predio")
            total_area = st.number_input("Área total (m²)", min_value=0.0, step=100.0)
        
        colL3, colL4 = st.columns(2)
        with colL3:
            land_type = st.selectbox("Tipo de tierra", ["Suelo agrícola","Suelo pecuario","Mixto","Bosque","Cuerpo de agua"])
            floodable = st.checkbox("¿Es inundable?")
        with colL4:
            slope = st.selectbox("Grado de inclinación", ["Plano","Ligero","Moderado","Escarpado"])
            reg_inmob = st.text_input("Matrícula inmobiliaria (opcional)")
        
        # Calidades en el predio (pueden diferir de la vivienda)
        st.subheader("Calidades en el predio")
        colW1, colW2 = st.columns(2)
        with colW1:
            land_water = st.selectbox("Calidad del agua (predio)", ["Buena","Regular","Mala","No tiene"])
            land_energy = st.selectbox("Calidad energía (predio)", ["Buena","Regular","Mala","No tiene"])
        with colW2:
            land_internet = st.selectbox("Calidad internet (predio)", ["Buena","Regular","Mala","No tiene"])
            land_sewage = st.selectbox("Alcantarillado (predio)", ["Si","No","Pozo séptico","Letrina"])
        land_waste = st.selectbox("Aseo (predio)", ["Si","No","Quema","Entierro"])
        
        submitted = st.form_submit_button("Siguiente →")
        if submitted:
            st.session_state.temp_data["housing"] = {
                "property_type": housing_type,
                "location": housing_loc,
                "cadastral_id": housing_cat,
                "built_area_m2": built_area,
                "patio_area_m2": patio_area,
                "water_quality": water_q,
                "energy_quality": energy_q,
                "internet_quality": internet_q,
                "sewage": sewage,
                "waste_management": waste
            }
            st.session_state.temp_data["land"] = {
                "property_type": land_prop_type,
                "land_name": land_name,
                "location": land_loc,
                "cadastral_id": land_cat,
                "total_area_m2": total_area,
                "land_type": land_type,
                "is_floodable": floodable,
                "water_quality": land_water,
                "slope_degree": slope,
                "energy_quality": land_energy,
                "internet_quality": land_internet,
                "sewage": land_sewage,
                "waste_management": land_waste,
                "real_estate_registration": reg_inmob
            }
            st.session_state.step = 4
            st.rerun()
    
    if st.button("← Atrás"):
        st.session_state.step = 2
        st.rerun()

# ========== PASO 4: Producción de bienes ==========
def step4():
    st.header("🌽 Paso 4: ¿Qué produce? (Bienes)")
    st.info("Puedes agregar uno o varios productos. Ejemplo: maíz, pescado, café, artesanías.")
    
    if "productions" not in st.session_state.temp_data:
        st.session_state.temp_data["productions"] = []
    
    # Mostrar productos ya agregados
    for i, prod in enumerate(st.session_state.temp_data["productions"]):
        with st.expander(f"📦 {prod.get('product_name','Producto')}"):
            st.write(f"Unidad: {prod.get('measure_unit')} | Cantidad: {prod.get('quantity_produced')}")
            if st.button(f"Eliminar producto {i}", key=f"del_prod_{i}"):
                st.session_state.temp_data["productions"].pop(i)
                st.rerun()
    
    # Formulario para nuevo producto
    with st.form("add_production_form"):
        col1, col2 = st.columns(2)
        with col1:
            prod_name = st.text_input("Nombre del producto *")
            unit = st.text_input("Unidad de medida (kg, litro, docena, etc.) *")
            area_used = st.number_input("Área ocupada (m²)", min_value=0.0)
        with col2:
            start_date = st.date_input("Fecha de inicio producción", value=None)
            frequency = st.selectbox("Periodicidad", ["Diaria","Semanal","Quincenal","Mensual","Trimestral","Anual"])
        
        col3, col4 = st.columns(2)
        with col3:
            quantity = st.number_input("Cantidad producida (por periodo)", min_value=0.0)
            total_price = st.number_input("Precio total por venta (COP)", min_value=0.0)
        with col4:
            unit_price = st.number_input("Precio por unidad de medida (COP)", min_value=0.0)
            quality = st.selectbox("Calidad del bien", ["Excelente","Buena","Regular","Baja"])
        
        add = st.form_submit_button("➕ Agregar producto")
        if add and prod_name and unit:
            st.session_state.temp_data["productions"].append({
                "product_name": prod_name,
                "measure_unit": unit,
                "occupied_area_m2": area_used,
                "start_date": start_date,
                "production_date": start_date,  # simplificado
                "frequency": frequency,
                "quantity_produced": quantity,
                "total_price": total_price,
                "unit_price": unit_price,
                "product_quality": quality
            })
            st.rerun()
    
    col_b, col_n = st.columns(2)
    with col_b:
        if st.button("← Atrás"):
            st.session_state.step = 3
            st.rerun()
    with col_n:
        if st.button("Siguiente →"):
            if len(st.session_state.temp_data["productions"]) == 0:
                st.warning("Al menos agrega un producto. Si no produce, escribe 'Ninguno'.")
            else:
                st.session_state.step = 5
                st.rerun()

# ========== PASO 5: Servicios ==========
def step5():
    st.header("🛠️ Paso 5: ¿Ofrece servicios?")
    if "services" not in st.session_state.temp_data:
        st.session_state.temp_data["services"] = []
    
    for i, serv in enumerate(st.session_state.temp_data["services"]):
        with st.expander(f"🔧 {serv.get('service_name','Servicio')}"):
            st.write(f"Unidad: {serv.get('measure_unit')} | Cantidad: {serv.get('quantity')}")
            if st.button(f"Eliminar servicio {i}", key=f"del_serv_{i}"):
                st.session_state.temp_data["services"].pop(i)
                st.rerun()
    
    with st.form("add_service_form"):
        col1, col2 = st.columns(2)
        with col1:
            serv_name = st.text_input("Nombre del servicio *")
            serv_unit = st.text_input("Unidad de medida (horas, días, viajes, etc.)")
        with col2:
            serv_area = st.number_input("Área ocupada para el servicio (m²)", min_value=0.0)
            serv_freq = st.selectbox("Periodicidad", ["Diaria","Semanal","Mensual","Eventual"])
        
        col3, col4 = st.columns(2)
        with col3:
            serv_quantity = st.number_input("Cantidad ofrecida (por periodo)", min_value=0.0)
            serv_price = st.number_input("Precio por servicio (COP)", min_value=0.0)
        with col4:
            serv_quality = st.selectbox("Calidad del servicio", ["Excelente","Buena","Regular","Baja"])
        
        add = st.form_submit_button("➕ Agregar servicio")
        if add and serv_name:
            st.session_state.temp_data["services"].append({
                "service_name": serv_name,
                "measure_unit": serv_unit,
                "occupied_area_m2": serv_area,
                "season_start": date.today(),
                "season_end": None,
                "frequency": serv_freq,
                "quantity": serv_quantity,
                "price": serv_price,
                "service_quality": serv_quality
            })
            st.rerun()
    
    col_b, col_save = st.columns(2)
    with col_b:
        if st.button("← Atrás"):
            st.session_state.step = 4
            st.rerun()
    with col_save:
        if st.button("✅ Guardar todo en la base de datos"):
            if len(st.session_state.temp_data["services"]) == 0:
                st.warning("Puede que no ofrezca servicios, igual puede guardar.")
            try:
                survey_id = save_survey(st.session_state.temp_data)
                st.success(f"¡Formulario guardado con éxito! ID: {survey_id}")
                st.balloons()
                # Reiniciar para un nuevo registro
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ========== CONTROL DE PASOS ==========
if st.session_state.step == 1:
    step1()
elif st.session_state.step == 2:
    step2()
elif st.session_state.step == 3:
    step3()
elif st.session_state.step == 4:
    step4()
elif st.session_state.step == 5:
    step5()