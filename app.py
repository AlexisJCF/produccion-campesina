import streamlit as st
from supabase import create_client, Client
from datetime import date, datetime
import os
import pandas as pd
import hashlib
import io
from PIL import Image
from dotenv import load_dotenv

# Cargar variables
load_dotenv()

# Configuración
st.set_page_config(
    page_title="COOPROGRESO - Sistema de Gestión",
    page_icon="🌾",
    layout="wide"
)

# Inicializar Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

# ========== AUTENTICACIÓN ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_admin(username, password):
    try:
        hashed = hash_password(password)
        result = supabase.table("admin_users").select("*").eq("username", username).eq("password_hash", hashed).execute()
        return len(result.data) > 0
    except:
        return False

# ========== FUNCIONES DE FOTOS ==========
def upload_photo(survey_id, photo_bytes, description, photo_type):
    try:
        counter = st.session_state.get("photo_counter", 0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{survey_id}_{photo_type}_{timestamp}_{counter}.jpg"
        
        # Subir a Supabase Storage
        response = supabase.storage.from_("survey_photos").upload(
            file_name,
            photo_bytes,
            {"content-type": "image/jpeg"}
        )
        
        # Obtener URL pública
        url = supabase.storage.from_("survey_photos").get_public_url(file_name)
        
        # Guardar referencia en BD
        supabase.table("survey_photos").insert({
            "survey_id": survey_id,
            "photo_url": url,
            "photo_description": description,
            "photo_type": photo_type
        }).execute()
        
        st.session_state.photo_counter = counter + 1
        return url
    except Exception as e:
        st.error(f"Error al subir foto: {e}")
        return None

# ========== FUNCIONES DE GUARDADO ==========
def save_survey(data):
    # Guardar registro principal
    survey_data = {
        "registration_date": data["registration_date"],
        "type": data["type"],
        "reason": data["reason"],
        "signature": data.get("signature", False),
        "synced": False
    }
    result = supabase.table("survey_registry").insert(survey_data).execute()
    survey_id = result.data[0]["id"]
    
    # Guardar familiares
    for member in data["family_members"]:
        member["survey_id"] = survey_id
        supabase.table("family_members").insert(member).execute()
    
    # Guardar vivienda
    housing_data = data["housing"]
    housing_data["survey_id"] = survey_id
    supabase.table("housing").insert(housing_data).execute()
    
    # Guardar predio
    land_data = data["land"]
    land_data["survey_id"] = survey_id
    supabase.table("land").insert(land_data).execute()
    
    # Guardar producciones
    for prod in data["productions"]:
        prod["survey_id"] = survey_id
        supabase.table("production_capacity").insert(prod).execute()
    
    # Guardar servicios
    for serv in data["services"]:
        serv["survey_id"] = survey_id
        supabase.table("service_capacity").insert(serv).execute()
    
    # Subir fotos
    if "temp_photos" in st.session_state and st.session_state.temp_photos:
        for photo in st.session_state.temp_photos:
            upload_photo(survey_id, photo["bytes"], photo["description"], photo["type"])
        st.session_state.temp_photos = []
        st.session_state.photo_counter = 0
    
    return survey_id

# ========== FUNCIONES DEL PANEL ADMIN ==========
def view_records():
    st.header("📋 Registros de Productores")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        tipo = st.selectbox("Filtrar por tipo", ["Todos", "INICIAL", "ACTUAL"])
    with col2:
        fecha_inicio = st.date_input("Fecha desde", value=None)
    with col3:
        fecha_fin = st.date_input("Fecha hasta", value=None)
    
    # Consulta
    query = supabase.table("survey_registry").select("*").order("created_at", desc=True)
    
    if tipo != "Todos":
        query = query.eq("type", tipo)
    if fecha_inicio:
        query = query.gte("registration_date", str(fecha_inicio))
    if fecha_fin:
        query = query.lte("registration_date", str(fecha_fin))
    
    result = query.execute()
    surveys = result.data
    
    if surveys:
        for survey in surveys:
            with st.expander(f"📝 Registro {survey['id'][:8]} - {survey['registration_date']} ({survey['type']})"):
                # Productor principal
                family = supabase.table("family_members").select("*").eq("survey_id", survey["id"]).eq("is_main", True).execute()
                if family.data:
                    main = family.data[0]
                    st.write(f"**Productor:** {main['nombres']} {main['apellidos']}")
                    st.write(f"**Teléfono:** {main.get('phone', 'No registrado')}")
                
                # Mostrar fotos
                photos = supabase.table("survey_photos").select("*").eq("survey_id", survey["id"]).execute()
                if photos.data:
                    st.write("**📸 Fotos:**")
                    cols = st.columns(3)
                    for i, photo in enumerate(photos.data[:3]):  # Mostrar máximo 3
                        with cols[i]:
                            st.image(photo["photo_url"], caption=photo["photo_description"], use_container_width=True)
                
                # Botones de acción
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Ver detalle completo", key=f"detail_{survey['id']}"):
                        show_full_survey(survey["id"])
                with col2:
                    if st.button(f"Exportar este registro", key=f"export_{survey['id']}"):
                        export_single_survey(survey["id"])
    else:
        st.info("No hay registros para mostrar")

def show_full_survey(survey_id):
    st.subheader("📄 Detalle completo del registro")
    
    # Obtener todos los datos
    family = supabase.table("family_members").select("*").eq("survey_id", survey_id).execute()
    housing = supabase.table("housing").select("*").eq("survey_id", survey_id).execute()
    land = supabase.table("land").select("*").eq("survey_id", survey_id).execute()
    productions = supabase.table("production_capacity").select("*").eq("survey_id", survey_id).execute()
    services = supabase.table("service_capacity").select("*").eq("survey_id", survey_id).execute()
    photos = supabase.table("survey_photos").select("*").eq("survey_id", survey_id).execute()
    
    tabs = st.tabs(["👨‍👩‍👧‍👦 Familia", "🏠 Vivienda", "🌳 Predio", "🌽 Producciones", "🛠️ Servicios", "📸 Fotos"])
    
    with tabs[0]:
        if family.data:
            df = pd.DataFrame(family.data)
            df = df[["nombres", "apellidos", "parentesco", "phone", "occupation", "sisben_category"]]
            st.dataframe(df)
    
    with tabs[1]:
        if housing.data:
            st.dataframe(pd.DataFrame(housing.data[0], index=[0]))
    
    with tabs[2]:
        if land.data:
            st.dataframe(pd.DataFrame(land.data[0], index=[0]))
    
    with tabs[3]:
        if productions.data:
            st.dataframe(pd.DataFrame(productions.data))
    
    with tabs[4]:
        if services.data:
            st.dataframe(pd.DataFrame(services.data))
    
    with tabs[5]:
        if photos.data:
            cols = st.columns(3)
            for i, photo in enumerate(photos.data):
                with cols[i % 3]:
                    st.image(photo["photo_url"], caption=f"{photo['photo_description']} ({photo['photo_type']})", use_container_width=True)
        else:
            st.info("No hay fotos")
    
    if st.button("Cerrar detalle"):
        st.rerun()

def export_single_survey(survey_id):
    # Exportar un registro específico
    tables = {
        "registro": supabase.table("survey_registry").select("*").eq("id", survey_id).execute(),
        "familiares": supabase.table("family_members").select("*").eq("survey_id", survey_id).execute(),
        "vivienda": supabase.table("housing").select("*").eq("survey_id", survey_id).execute(),
        "predio": supabase.table("land").select("*").eq("survey_id", survey_id).execute(),
        "producciones": supabase.table("production_capacity").select("*").eq("survey_id", survey_id).execute(),
        "servicios": supabase.table("service_capacity").select("*").eq("survey_id", survey_id).execute()
    }
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for name, data in tables.items():
            if data.data:
                df = pd.DataFrame(data.data)
                df.to_excel(writer, sheet_name=name[:31], index=False)
    
    st.download_button(
        label="📥 Descargar Excel",
        data=output.getvalue(),
        file_name=f"registro_{survey_id[:8]}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def show_statistics():
    st.header("📈 Estadísticas Generales")
    
    # Métricas
    total = supabase.table("survey_registry").select("count", count="exact").execute()
    inicial = supabase.table("survey_registry").select("count", count="exact").eq("type", "INICIAL").execute()
    actual = supabase.table("survey_registry").select("count", count="exact").eq("type", "ACTUAL").execute()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total registros", total.count)
    with col2:
        st.metric("Iniciales", inicial.count)
    with col3:
        st.metric("Actualizaciones", actual.count)
    with col4:
        if total.count > 0:
            st.metric("% Actualizados", f"{actual.count/total.count*100:.1f}%")
    
    # Productos más comunes
    st.subheader("🌽 Top 10 productos")
    products = supabase.table("production_capacity").select("product_name").execute()
    if products.data:
        df = pd.DataFrame(products.data)
        top = df["product_name"].value_counts().head(10)
        st.bar_chart(top)
    
    # Servicios más comunes
    st.subheader("🛠️ Top 10 servicios")
    services = supabase.table("service_capacity").select("service_name").execute()
    if services.data:
        df = pd.DataFrame(services.data)
        top = df["service_name"].value_counts().head(10)
        st.bar_chart(top)

def export_all_data():
    st.header("📤 Exportar todos los datos")
    
    format_type = st.radio("Formato", ["Excel", "CSV (archivos separados)"])
    
    if st.button("📥 Generar exportación"):
        tables = ["survey_registry", "family_members", "housing", "land", "production_capacity", "service_capacity"]
        
        if format_type == "Excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for table in tables:
                    data = supabase.table(table).select("*").execute()
                    if data.data:
                        df = pd.DataFrame(data.data)
                        df.to_excel(writer, sheet_name=table[:31], index=False)
            
            st.download_button(
                label="📥 Descargar Excel completo",
                data=output.getvalue(),
                file_name=f"cooprogreso_datos_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            for table in tables:
                data = supabase.table(table).select("*").execute()
                if data.data:
                    df = pd.DataFrame(data.data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label=f"📥 Descargar {table}.csv",
                        data=csv,
                        file_name=f"{table}_{date.today()}.csv",
                        mime="text/csv"
                    )

def login_page():
    st.sidebar.title("🔐 Acceso Administrador")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if st.sidebar.button("Iniciar sesión"):
        if check_admin(username, password):
            st.session_state.authenticated = True
            st.session_state.admin_username = username
            st.success("¡Bienvenido!")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    
    if st.session_state.authenticated:
        st.sidebar.success(f"✅ Conectado como: {username}")
        return True
    return False

# ========== FORMULARIO PRINCIPAL ==========
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
        
        st.subheader("👤 Productor principal")
        col1, col2, col3 = st.columns(3)
        with col1:
            nombres = st.text_input("Nombres *")
            apellidos = st.text_input("Apellidos *")
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
                st.error("Nombres, apellidos e identificación son obligatorios.")

def step2():
    st.header("👨‍👩‍👧‍👦 Paso 2: Otros miembros de la familia")
    
    if "extra_family" not in st.session_state:
        st.session_state.extra_family = []
    
    for i, m in enumerate(st.session_state.extra_family):
        with st.expander(f"{m.get('nombres','')} {m.get('apellidos','')} - {m.get('parentesco','')}"):
            st.write(f"Teléfono: {m.get('phone','')}")
            if st.button(f"Eliminar", key=f"del_fam_{i}"):
                st.session_state.extra_family.pop(i)
                st.rerun()
    
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
        
        if st.form_submit_button("➕ Agregar familiar"):
            if fam_nombres and fam_apellidos:
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
            st.session_state.temp_data["family_members"].extend(st.session_state.extra_family)
            st.session_state.step = 3
            st.rerun()

def step3():
    st.header("🏠 Paso 3: Vivienda, Predio y Fotos")
    
    with st.form("housing_land_form"):
        st.subheader("Datos de la vivienda")
        col1, col2 = st.columns(2)
        with col1:
            housing_type = st.text_input("Tipo de propiedad (vivienda)")
            housing_loc = st.text_input("Ubicación geográfica")
            housing_cat = st.text_input("ID Catastral")
        with col2:
            built_area = st.number_input("Área construida (m²)", min_value=0.0, step=10.0)
            patio_area = st.number_input("Área de patio (m²)", min_value=0.0, step=10.0)
        
        st.subheader("Calidades (vivienda)")
        colq1, colq2, colq3 = st.columns(3)
        with colq1:
            water_q = st.selectbox("Calidad del agua", ["Buena","Regular","Mala","No tiene"])
            energy_q = st.selectbox("Calidad energía", ["Buena","Regular","Mala","No tiene"])
        with colq2:
            internet_q = st.selectbox("Calidad internet", ["Buena","Regular","Mala","No tiene"])
            sewage = st.selectbox("Alcantarillado", ["Si","No","Pozo séptico","Letrina"])
        with colq3:
            waste = st.selectbox("Recolección de aseo", ["Si","No","Quema","Entierro"])
        
        st.subheader("🌳 Datos del predio")
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
        
        st.subheader("Calidades (predio)")
        colW1, colW2 = st.columns(2)
        with colW1:
            land_water = st.selectbox("Calidad del agua (predio)", ["Buena","Regular","Mala","No tiene"])
            land_energy = st.selectbox("Calidad energía (predio)", ["Buena","Regular","Mala","No tiene"])
        with colW2:
            land_internet = st.selectbox("Calidad internet (predio)", ["Buena","Regular","Mala","No tiene"])
            land_sewage = st.selectbox("Alcantarillado (predio)", ["Si","No","Pozo séptico","Letrina"])
        land_waste = st.selectbox("Aseo (predio)", ["Si","No","Quema","Entierro"])
        
        # Sección de fotos
        st.subheader("📸 Fotografías")
        st.info("Puedes tomar fotos de la vivienda, predio, cultivos o instalaciones")
        
        if "photo_counter" not in st.session_state:
            st.session_state.photo_counter = 0
        if "temp_photos" not in st.session_state:
            st.session_state.temp_photos = []
        
        photo_type = st.selectbox("Tipo de foto", ["PREDIO", "VIVIENDA", "PRODUCTO", "SERVICIO", "OTRO"])
        photo_desc = st.text_input("Descripción de la foto")
        
        camera_photo = st.camera_input("📷 Tomar foto con la cámara")
        uploaded_file = st.file_uploader("📤 O subir foto desde el dispositivo", type=["jpg", "jpeg", "png"])
        
        if (camera_photo or uploaded_file) and photo_desc:
            img_bytes = camera_photo.getvalue() if camera_photo else uploaded_file.getvalue()
            st.session_state.temp_photos.append({
                "bytes": img_bytes,
                "description": photo_desc,
                "type": photo_type
            })
            st.success(f"Foto agregada ({len(st.session_state.temp_photos)} en total)")
            st.rerun()
        
        if st.session_state.temp_photos:
            st.write(f"**Fotos tomadas: {len(st.session_state.temp_photos)}**")
            cols = st.columns(4)
            for i, photo in enumerate(st.session_state.temp_photos):
                with cols[i % 4]:
                    try:
                        img = Image.open(io.BytesIO(photo["bytes"]))
                        st.image(img, caption=photo["description"], use_container_width=True)
                        if st.button(f"🗑️", key=f"del_photo_{i}"):
                            st.session_state.temp_photos.pop(i)
                            st.rerun()
                    except:
                        pass
        
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

def step4():
    st.header("🌽 Paso 4: ¿Qué produce? (Bienes)")
    
    if "productions" not in st.session_state.temp_data:
        st.session_state.temp_data["productions"] = []
    
    for i, prod in enumerate(st.session_state.temp_data["productions"]):
        with st.expander(f"📦 {prod.get('product_name','Producto')}"):
            st.write(f"Unidad: {prod.get('measure_unit')} | Cantidad: {prod.get('quantity_produced')}")
            if st.button(f"Eliminar", key=f"del_prod_{i}"):
                st.session_state.temp_data["productions"].pop(i)
                st.rerun()
    
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
        
        if st.form_submit_button("➕ Agregar producto"):
            if prod_name and unit:
                st.session_state.temp_data["productions"].append({
                    "product_name": prod_name,
                    "measure_unit": unit,
                    "occupied_area_m2": area_used,
                    "start_date": start_date,
                    "production_date": start_date,
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
                st.warning("Agrega al menos un producto o escribe 'Ninguno'")
            else:
                st.session_state.step = 5
                st.rerun()

def step5():
    st.header("🛠️ Paso 5: ¿Ofrece servicios?")
    
    if "services" not in st.session_state.temp_data:
        st.session_state.temp_data["services"] = []
    
    for i, serv in enumerate(st.session_state.temp_data["services"]):
        with st.expander(f"🔧 {serv.get('service_name','Servicio')}"):
            st.write(f"Unidad: {serv.get('measure_unit')} | Cantidad: {serv.get('quantity')}")
            if st.button(f"Eliminar", key=f"del_serv_{i}"):
                st.session_state.temp_data["services"].pop(i)
                st.rerun()
    
    with st.form("add_service_form"):
        col1, col2 = st.columns(2)
        with col1:
            serv_name = st.text_input("Nombre del servicio *")
            serv_unit = st.text_input("Unidad de medida (horas, días, viajes, etc.)")
        with col2:
            serv_area = st.number_input("Área ocupada (m²)", min_value=0.0)
            serv_freq = st.selectbox("Periodicidad", ["Diaria","Semanal","Mensual","Eventual"])
        
        col3, col4 = st.columns(2)
        with col3:
            serv_quantity = st.number_input("Cantidad ofrecida (por periodo)", min_value=0.0)
            serv_price = st.number_input("Precio por servicio (COP)", min_value=0.0)
        with col4:
            serv_quality = st.selectbox("Calidad del servicio", ["Excelente","Buena","Regular","Baja"])
        
        if st.form_submit_button("➕ Agregar servicio"):
            if serv_name:
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
            try:
                survey_id = save_survey(st.session_state.temp_data)
                st.success(f"✅ ¡Formulario guardado con éxito! ID: {survey_id[:8]}")
                st.balloons()
                
                # Limpiar sesión
                for key in list(st.session_state.keys()):
                    if key not in ["authenticated", "admin_username"]:
                        del st.session_state[key]
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ========== MAIN ==========
def main():
    # Inicializar session state
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "temp_data" not in st.session_state:
        st.session_state.temp_data = {}
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "admin_username" not in st.session_state:
        st.session_state.admin_username = None
    
    # Título
    st.title("🌾 COOPROGRESO - Sistema de Capacidad Productiva")
    
    # Barra lateral de administración
    with st.sidebar:
        st.markdown("---")
        if not st.session_state.authenticated:
            login_page()
        else:
            st.success(f"✅ Conectado: {st.session_state.admin_username}")
            if st.button("🚪 Cerrar sesión"):
                st.session_state.authenticated = False
                st.session_state.admin_username = None
                st.rerun()
            
            st.markdown("---")
            st.subheader("📊 Panel de Administración")
            
            admin_option = st.radio(
                "Selecciona:",
                ["📋 Ver Registros", "📈 Estadísticas", "📤 Exportar Datos"]
            )
            
            if admin_option == "📋 Ver Registros":
                view_records()
            elif admin_option == "📈 Estadísticas":
                show_statistics()
            elif admin_option == "📤 Exportar Datos":
                export_all_data()
    
    # Formulario principal (solo si no está autenticado o se quiere llenar)
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

if __name__ == "__main__":
    main()
